"""
Deterministic Resume Security Audit & Prompt-Injection Defense Service for CareerLens AI
Provides multi-layered deterministic scanning for:
  - Direct and indirect prompt-injection directives
  - Hidden Unicode format, zero-width, and bidirectional control characters
  - Obfuscated/encoded instructions (zero-width fragmentation, base64, hex, homoglyphs)
  - Dangerous URI schemes and code injection patterns
  - Bounded memory and execution time to prevent DoS/ReDoS

Design Principles:
  - Detection is a defense-in-depth layer, not a guarantee that every malicious payload is caught.
  - Match scoring and evidence verification remain deterministic in application code.
  - Original document content is strictly preserved; never silently modified.
  - Safe truncation, escaping, and bounded processing ensure scanner safety.
"""

import re
import html
import time
import base64
import binascii
import unicodedata
import logging
from typing import Dict, List, Any, Optional, Tuple

from config import (
    SECURITY_MAX_SCAN_LENGTH,
    SECURITY_MAX_FINDINGS,
    SECURITY_MAX_SNIPPET_LENGTH,
    SECURITY_STATUSES,
    SECURITY_ACTIONS,
    SECURITY_POLICY,
    SECURITY_INJECTION_PATTERNS,
    SECURITY_UNICODE_FORMAT_CHARS,
    SECURITY_SCANNER_LIMITATIONS
)

logger = logging.getLogger("careerlens.security")

# Pre-compile injection patterns for linear-time scanning
COMPILED_INJECTION_PATTERNS = [
    {
        **rule,
        "_compiled": re.compile(rule["pattern"], re.IGNORECASE)
    }
    for rule in SECURITY_INJECTION_PATTERNS
]

# Base64 string detector (min length 16, valid padding/charset)
BASE64_PATTERN = re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/])')

# Hex string detector (e.g. \x69\x67... or long 0x... hex blocks)
HEX_PATTERN = re.compile(r'(?:(?:\\x[0-9a-fA-F]{2}){4,})|(?:0x[0-9a-fA-F]{8,})')

# Common Cyrillic homoglyphs mapping to Latin
HOMOGLYPH_MAP = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'і': 'i',
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P',
    'С': 'C', 'Т': 'T', 'Х': 'X'
}


class SecurityAuditService:
    """
    Deterministic security scanning engine for resumes and job descriptions.
    """

    def __init__(self):
        self.policy = SECURITY_POLICY
        self.limitations = list(SECURITY_SCANNER_LIMITATIONS)

    def scan_text(
        self,
        text: str,
        filename: Optional[str] = None,
        source_type: str = "resume",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes comprehensive deterministic security audit on input text.
        Returns a structured SecurityAuditReport dictionary.
        """
        start_time = time.perf_counter()
        audit_id = f"aud_{int(time.time() * 1000)}"

        # 1. Bounded Input Length Check
        if text is None:
            text = ""

        raw_length = len(text)
        is_truncated = False
        scan_text = text

        if raw_length > SECURITY_MAX_SCAN_LENGTH:
            scan_text = text[:SECURITY_MAX_SCAN_LENGTH]
            is_truncated = True

        findings: List[Dict[str, Any]] = []

        if is_truncated:
            findings.append({
                "id": f"fnd_trunc_{len(findings)+1}",
                "severity": "warning",
                "category": "scanner_notice",
                "title": "Document Input Truncated for Scanner Safety (Incomplete Scan)",
                "description": f"Input document length ({raw_length:,} chars) exceeded maximum scan budget ({SECURITY_MAX_SCAN_LENGTH:,} chars). Scanning was bounded to the first 1MB to prevent resource exhaustion. Unscanned content cannot be verified as safe.",
                "evidence_snippet": self._truncate_snippet(scan_text[-100:]),
                "start_offset": SECURITY_MAX_SCAN_LENGTH,
                "end_offset": raw_length,
                "line_number": scan_text.count("\n") + 1,
                "remediation": "Review document length and split into smaller sections if necessary.",
                "false_positive_note": "Expected behavior for exceptionally large text documents."
            })

        # Empty document check
        if not scan_text.strip():
            scan_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "audit_id": audit_id,
                "filename": filename,
                "status": "warning",
                "action_taken": "warned",
                "risk_score": 10,
                "findings_count": {"critical": 0, "warning": 1, "info": 0, "total": 1},
                "findings": [{
                    "id": "fnd_empty",
                    "severity": "warning",
                    "category": "document_integrity",
                    "title": "Empty Document Content",
                    "description": "The provided text contains no readable characters to audit.",
                    "evidence_snippet": "[Empty content]",
                    "start_offset": 0,
                    "end_offset": 0,
                    "line_number": 1,
                    "remediation": "Ensure the resume was properly extracted and contains text.",
                    "false_positive_note": None
                }],
                "hidden_characters_summary": {
                    "total_hidden_chars": 0,
                    "categories": {},
                    "characters_detected": [],
                    "bidi_overrides_detected": 0,
                    "zero_width_detected": 0
                },
                "explanation": "No text content was available for security inspection.",
                "recommendations": ["Re-upload a non-empty document with accessible text."],
                "scanner_limitations": self.limitations,
                "scan_metadata": {
                    "characters_scanned": 0,
                    "scan_duration_ms": scan_duration_ms,
                    "source_type": source_type,
                    "is_truncated": False
                },
                "is_safe_for_llm": False
            }

        # 2. Hidden Characters & Unicode Formatting Analysis
        hidden_char_findings, hidden_summary = self._analyze_hidden_characters(scan_text)
        for hf in hidden_char_findings:
            if len(findings) < SECURITY_MAX_FINDINGS:
                findings.append(hf)

        # 3. Direct Prompt Injection & Instruction Patterns
        direct_findings = self._scan_injection_patterns(scan_text)
        for df in direct_findings:
            if len(findings) < SECURITY_MAX_FINDINGS:
                findings.append(df)

        # 4. De-obfuscation Analysis (Zero-Width Stripping, Base64, Hex, Homoglyphs)
        obfuscation_findings = self._scan_obfuscated_instructions(scan_text, direct_findings)
        for of in obfuscation_findings:
            if len(findings) < SECURITY_MAX_FINDINGS:
                findings.append(of)

        # 5. Metadata Scanning (if metadata supplied from PDF/DOCX)
        if metadata and isinstance(metadata, dict):
            meta_findings = self._scan_document_metadata(metadata)
            for mf in meta_findings:
                if len(findings) < SECURITY_MAX_FINDINGS:
                    findings.append(mf)

        # 6. Aggregate Findings & Determine Policy Status
        critical_count = sum(1 for f in findings if f["severity"] == "critical")
        warning_count = sum(1 for f in findings if f["severity"] == "warning")
        info_count = sum(1 for f in findings if f["severity"] == "info")
        total_findings = len(findings)

        # Risk Score Calculation (0 - 100)
        # Critical: +40 each, Warning: +15 each, Info: +2 each
        risk_score = min(100, (critical_count * 40) + (warning_count * 15) + (info_count * 2))

        if critical_count > 0:
            status = SECURITY_STATUSES["BLOCKED"]
            action_taken = SECURITY_ACTIONS["BLOCKED"]
            is_safe_for_llm = False
            explanation = (
                f"Document contains {critical_count} critical security alert(s) including explicit prompt-injection "
                f"or adversarial overrides. Downstream unconstrained LLM calls are blocked. Deterministic matching "
                f"and qualification analysis continue safely in application code."
            )
        elif warning_count > 0:
            status = SECURITY_STATUSES["WARNING"]
            action_taken = SECURITY_ACTIONS["WARNED"]
            is_safe_for_llm = not is_truncated
            if is_truncated:
                explanation = (
                    f"Document exceeded maximum scan budget ({SECURITY_MAX_SCAN_LENGTH:,} chars) and was truncated. "
                    f"The scan is incomplete ({total_findings} finding(s)); downstream unconstrained LLM processing is restricted."
                )
            else:
                explanation = (
                    f"Document contains {warning_count} warning finding(s) (e.g. unusual invisible formatting or suspicious "
                    f"patterns). Processing continues with isolation boundaries and visible warnings."
                )
        else:
            status = SECURITY_STATUSES["PASSED"]
            action_taken = SECURITY_ACTIONS["ALLOWED"]
            is_safe_for_llm = True
            explanation = (
                f"No prompt-injection directives or suspicious invisible formatting detected ({total_findings} informational finding(s)). "
                f"Document appears normal."
            )

        # Recommendations list
        recommendations = self._generate_recommendations(critical_count, warning_count, hidden_summary)

        scan_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "audit_id": audit_id,
            "filename": filename,
            "status": status,
            "action_taken": action_taken,
            "risk_score": risk_score,
            "findings_count": {
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count,
                "total": total_findings
            },
            "findings": findings,
            "hidden_characters_summary": hidden_summary,
            "explanation": explanation,
            "recommendations": recommendations,
            "scanner_limitations": self.limitations,
            "scan_metadata": {
                "characters_scanned": len(scan_text),
                "total_lines": scan_text.count("\n") + 1,
                "scan_duration_ms": scan_duration_ms,
                "source_type": source_type,
                "is_truncated": is_truncated
            },
            "is_safe_for_llm": is_safe_for_llm
        }

    # ─── Internal Scanners ───

    def _analyze_hidden_characters(self, text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Inspects text for Unicode format, zero-width, bidirectional, and control characters.
        Never strips characters from the source text; only records occurrences.
        Distinguishes between malicious Trojan Source overrides and benign artifacts.
        """
        findings: List[Dict[str, Any]] = []
        char_counts: Dict[str, Dict[str, Any]] = {}
        category_counts: Dict[str, int] = {}
        bidi_overrides_detected = 0
        zero_width_detected = 0
        total_hidden_chars = 0

        # Build line offset map for accurate line number reporting
        line_offsets = [0]
        for m in re.finditer(r'\n', text):
            line_offsets.append(m.end())

        def get_line_num(offset: int) -> int:
            # Binary search or scan
            import bisect
            return bisect.bisect_right(line_offsets, offset)

        for idx, ch in enumerate(text):
            cat = unicodedata.category(ch)
            # Inspect Format (Cf), Control (Cc), and specific registered chars
            is_registered = ch in SECURITY_UNICODE_FORMAT_CHARS
            is_cf = cat == "Cf"
            is_cc = cat == "Cc" and ch not in ("\n", "\r", "\t")
            is_tag = "\U000e0000" <= ch <= "\U000e007f"

            if is_registered or is_cf or is_cc or is_tag:
                total_hidden_chars += 1
                category_counts[cat] = category_counts.get(cat, 0) + 1

                reg_meta = SECURITY_UNICODE_FORMAT_CHARS.get(ch, {})
                codepoint = f"U+{ord(ch):04X}"
                char_name = reg_meta.get("name") or unicodedata.name(ch, f"UNKNOWN CONTROL ({codepoint})")

                if codepoint not in char_counts:
                    char_counts[codepoint] = {
                        "codepoint": codepoint,
                        "name": char_name,
                        "category": cat,
                        "count": 0,
                        "first_offset": idx,
                        "first_line": get_line_num(idx),
                        "registered_severity": reg_meta.get("severity", "warning"),
                        "risk": reg_meta.get("risk", "Unexpected format/control character.")
                    }
                char_counts[codepoint]["count"] += 1

                # Track bidi overrides (Trojan Source attack vector)
                if ch in ("\u202d", "\u202e"):
                    bidi_overrides_detected += 1
                if ch in ("\u200b", "\u200c", "\u200d", "\u2060"):
                    zero_width_detected += 1

        # Synthesize character findings
        for cp, info in char_counts.items():
            count = info["count"]
            raw_severity = info["registered_severity"]
            risk_desc = info["risk"]

            # Nuanced severity calibration:
            # - BOM (\ufeff): benign if <= 2; warning if widespread
            # - Soft Hyphen (\u00ad): benign in Word exports (< 25); warning if abnormally dense
            # - Bidi overrides (RLO/LRO): always CRITICAL (Trojan Source)
            # - Zero-width space (\u200b): warning if <= 10; critical if dense (> 10)
            if cp == "U+FEFF":
                severity = "info" if count <= 2 else "warning"
                nuance = "Byte Order Marks often appear benignly at the start of UTF-8 text files."
            elif cp == "U+00AD":
                severity = "info" if count <= 30 else "warning"
                nuance = "Soft hyphens are standard discretionary hyphens generated by Word processors to format line breaks."
            elif cp in ("U+202D", "U+202E"):
                severity = "critical"
                nuance = "Bidirectional overrides (RLO/LRO) can reverse displayed text order to mask payloads or file extensions."
            elif cp in ("U+200B", "U+2060"):
                severity = "critical" if count > 10 else "warning"
                nuance = "Zero-width characters have no visual display and can be used to fragment prompt injection keywords."
            elif cp in ("U+200C", "U+200D"):
                severity = "warning"
                nuance = "Zero-width joiners/non-joiners are legitimate in Persian, Arabic, and Indic scripts, but anomalous in standard Latin text."
            else:
                severity = raw_severity
                nuance = "Uncommon Unicode formatting character."

            evidence = self._make_character_evidence(text, info["first_offset"], cp, info["name"])

            findings.append({
                "id": f"fnd_unicode_{cp.replace('+', '_')}",
                "severity": severity,
                "category": "hidden_characters",
                "title": f"Invisible Character: {info['name']} ({cp})",
                "description": f"Found {count} occurrence(s) of {info['name']} [{cp}] in character category '{info['category']}'. {risk_desc}",
                "evidence_snippet": evidence,
                "start_offset": info["first_offset"],
                "end_offset": info["first_offset"] + 1,
                "line_number": info["first_line"],
                "remediation": f"Verify whether {info['name']} is required for international text or remove unnecessary invisible characters.",
                "false_positive_note": nuance
            })

        summary = {
            "total_hidden_chars": total_hidden_chars,
            "categories": category_counts,
            "characters_detected": list(char_counts.values()),
            "bidi_overrides_detected": bidi_overrides_detected,
            "zero_width_detected": zero_width_detected
        }

        return findings, summary

    def _scan_injection_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans text against compiled prompt-injection and instruction patterns.
        Records exact offsets, line numbers, and safely escaped evidence snippets.
        """
        findings: List[Dict[str, Any]] = []

        line_offsets = [0]
        for m in re.finditer(r'\n', text):
            line_offsets.append(m.end())

        def get_line_num(offset: int) -> int:
            import bisect
            return bisect.bisect_right(line_offsets, offset)

        for rule in COMPILED_INJECTION_PATTERNS:
            if len(findings) >= SECURITY_MAX_FINDINGS:
                break
            regex = rule["_compiled"]
            for match in regex.finditer(text):
                start, end = match.span()
                line = get_line_num(start)
                snippet = self._make_snippet_context(text, start, end)

                findings.append({
                    "id": f"fnd_inj_{len(findings)+1}",
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "title": rule["title"],
                    "description": rule["description"],
                    "evidence_snippet": snippet,
                    "start_offset": start,
                    "end_offset": end,
                    "line_number": line,
                    "remediation": rule["remediation"],
                    "false_positive_note": "If this resume discusses AI Prompt Engineering or cybersecurity research, this pattern may be a legitimate technical discussion rather than an active attack."
                })

                if len(findings) >= SECURITY_MAX_FINDINGS:
                    break

        return findings

    def _scan_obfuscated_instructions(
        self,
        raw_text: str,
        existing_findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Checks for obfuscated prompt-injection vectors:
          1. Zero-width character fragmentation: stripped text matches injection rules.
          2. Base64 payload decoding.
          3. Hex-encoded strings.
          4. Mixed-script homoglyphs.
        """
        obf_findings: List[Dict[str, Any]] = []
        existing_titles = set(f["title"] for f in existing_findings)

        # 1. Zero-Width De-obfuscation Check
        # Build sanitized representation strictly in a temporary buffer for scanning
        sanitized_chars = []
        offset_map = []
        for orig_idx, ch in enumerate(raw_text):
            if ch not in ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad", "\u202a", "\u202b", "\u202c", "\u202d", "\u202e"):
                sanitized_chars.append(ch)
                offset_map.append(orig_idx)

        deobf_text = "".join(sanitized_chars)

        # If characters were removed, check if de-obfuscated text triggers injection rules that were missed
        if len(deobf_text) < len(raw_text):
            for rule in COMPILED_INJECTION_PATTERNS:
                regex = rule["_compiled"]
                for match in regex.finditer(deobf_text):
                    m_start, m_end = match.span()
                    orig_start = offset_map[m_start] if m_start < len(offset_map) else 0
                    orig_end = offset_map[m_end - 1] + 1 if m_end - 1 < len(offset_map) else orig_start + 1

                    # Check if this exact text was already flagged by direct scanner
                    raw_slice = raw_text[orig_start:orig_end]
                    if not regex.search(raw_slice):
                        # Pattern ONLY matched after stripping invisible characters!
                        snippet = self._make_snippet_context(raw_text, orig_start, orig_end)
                        obf_findings.append({
                            "id": f"fnd_obf_zw_{len(obf_findings)+1}",
                            "severity": "critical",
                            "category": "obfuscation",
                            "title": "Zero-Width Fragmented Prompt Injection",
                            "description": f"Adversarial instruction text was fragmented using invisible zero-width characters to evade keyword filters: '{rule['title']}'.",
                            "evidence_snippet": snippet,
                            "start_offset": orig_start,
                            "end_offset": orig_end,
                            "line_number": raw_text[:orig_start].count("\n") + 1,
                            "remediation": "Remove concealed zero-width character sequences and instruction overrides.",
                            "false_positive_note": "Zero-width fragmentation of instruction phrases is strongly correlated with adversarial evasion."
                        })

        # 2. Base64 Encoded Payload Check (supports bounded nested decoding up to depth 3)
        for b64_match in BASE64_PATTERN.finditer(raw_text):
            b64_str = b64_match.group(0)
            curr_str = b64_str
            depth = 0
            max_depth = 3
            while depth < max_depth:
                try:
                    decoded_bytes = base64.b64decode(curr_str, validate=True)
                    if len(decoded_bytes) > 100_000:
                        break  # Bounded size check against compression bombs
                    decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
                    depth += 1
                    if len(decoded_str) >= 8 and any(c.isalnum() for c in decoded_str):
                        found_rule = None
                        for rule in COMPILED_INJECTION_PATTERNS:
                            if rule["_compiled"].search(decoded_str):
                                found_rule = rule
                                break
                        if found_rule:
                            start, end = b64_match.span()
                            title_prefix = f"Nested Base64 (Depth {depth})" if depth > 1 else "Base64 Obfuscated"
                            obf_findings.append({
                                "id": f"fnd_obf_b64_{len(obf_findings)+1}",
                                "severity": "critical",
                                "category": "obfuscation",
                                "title": f"{title_prefix} Prompt Injection",
                                "description": f"Decoded base64 payload (depth {depth}) contained an adversarial directive: '{found_rule['title']}' -> '{decoded_str[:60]}...'",
                                "evidence_snippet": self._truncate_snippet(b64_str),
                                "start_offset": start,
                                "end_offset": end,
                                "line_number": raw_text[:start].count("\n") + 1,
                                "remediation": "Remove encoded instruction payloads from resume.",
                                "false_positive_note": "Ensure base64 strings represent genuine application data rather than encoded instructions."
                            })
                            break
                        # Check if decoded string contains further base64 payload
                        nested_match = BASE64_PATTERN.search(decoded_str)
                        if nested_match and nested_match.group(0) != curr_str:
                            curr_str = nested_match.group(0)
                        else:
                            break
                    else:
                        break
                except (binascii.Error, ValueError):
                    break

        # 3. Hex Encoded Payload Check
        for hex_match in HEX_PATTERN.finditer(raw_text):
            hex_str = hex_match.group(0)
            try:
                # Clean prefix
                clean_hex = re.sub(r'\\x|0x', '', hex_str)
                if len(clean_hex) % 2 == 0:
                    decoded = bytes.fromhex(clean_hex).decode("utf-8", errors="ignore")
                    for rule in COMPILED_INJECTION_PATTERNS:
                        if rule["_compiled"].search(decoded):
                            start, end = hex_match.span()
                            obf_findings.append({
                                "id": f"fnd_obf_hex_{len(obf_findings)+1}",
                                "severity": "critical",
                                "category": "obfuscation",
                                "title": "Hex-Encoded Prompt Injection",
                                "description": f"Decoded hexadecimal string contains an adversarial directive: '{rule['title']}' -> '{decoded[:60]}...'",
                                "evidence_snippet": self._truncate_snippet(hex_str),
                                "start_offset": start,
                                "end_offset": end,
                                "line_number": raw_text[:start].count("\n") + 1,
                                "remediation": "Remove hex-encoded commands.",
                                "false_positive_note": None
                            })
                            break
            except Exception:
                pass

        # 4. Mixed-Script Homoglyph & Unicode Normalization Check
        homoglyph_finding = self._check_homoglyphs(raw_text)
        if homoglyph_finding:
            obf_findings.append(homoglyph_finding)

        return obf_findings

    def _check_homoglyphs(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detects Latin words where characters are substituted with Cyrillic homoglyphs
        or fullwidth / mathematical alphanumeric Unicode symbols to evade standard keyword detection.
        """
        # 1. Unicode NFKC Normalization Check (catches fullwidth, mathematical bold/italic, etc.)
        nfkc_text = unicodedata.normalize('NFKC', text)
        if nfkc_text != text:
            for rule in COMPILED_INJECTION_PATTERNS:
                regex = rule["_compiled"]
                match = regex.search(nfkc_text)
                if match and not regex.search(text):
                    start, end = match.span()
                    snippet = self._truncate_snippet(f"Normalized: {nfkc_text[start:end]}")
                    return {
                        "id": "fnd_obf_nfkc",
                        "severity": "critical",
                        "category": "obfuscation",
                        "title": "Unicode Normalization / Font Homoglyph Evasion",
                        "description": f"Detected fullwidth or compatibility Unicode font evasion disguising an adversarial directive: '{rule['title']}'.",
                        "evidence_snippet": snippet,
                        "start_offset": start,
                        "end_offset": end,
                        "line_number": text[:start].count("\n") + 1,
                        "remediation": "Use standard Latin alphanumeric characters without mathematical font formatting.",
                        "false_positive_note": "Legitimate resumes do not format prompt overrides in mathematical or fullwidth scripts."
                    }

        # 2. Cyrillic Homoglyph Map Check
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
        if not has_cyrillic:
            return None

        # Build normalized text replacing homoglyphs
        normalized_text = "".join(HOMOGLYPH_MAP.get(c, c) for c in text)
        if normalized_text == text:
            return None

        # Check if normalized text triggers any injection rules that raw text did not trigger
        for rule in COMPILED_INJECTION_PATTERNS:
            regex = rule["_compiled"]
            match = regex.search(normalized_text)
            if match and not regex.search(text):
                start, end = match.span()
                snippet = self._make_snippet_context(text, start, end)
                return {
                    "id": "fnd_obf_homoglyph",
                    "severity": "critical",
                    "category": "obfuscation",
                    "title": "Homoglyph Evasion (Mixed-Script Substitution)",
                    "description": f"Detected Cyrillic homoglyph character substitution disguising an adversarial directive: '{rule['title']}' -> '{normalized_text[start:end]}'.",
                    "evidence_snippet": snippet,
                    "start_offset": start,
                    "end_offset": end,
                    "line_number": text[:start].count("\n") + 1,
                    "remediation": "Use standard single-script characters throughout resume text.",
                    "false_positive_note": "Legitimate bilingual resumes typically do not mix Latin and Cyrillic characters to conceal instruction override directives."
                }
        return None

    def _scan_document_metadata(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scans document metadata fields (e.g. PDF Author, Subject, Title) for injection commands.
        """
        findings = []
        for key, value in metadata.items():
            if isinstance(value, str) and value.strip():
                for rule in COMPILED_INJECTION_PATTERNS:
                    if rule["_compiled"].search(value):
                        findings.append({
                            "id": f"fnd_meta_{key}",
                            "severity": "critical",
                            "category": "prompt_injection",
                            "title": f"Document Metadata Injection: {key.title()}",
                            "description": f"Document metadata field '{key}' contains prompt-injection directive: '{rule['title']}'.",
                            "evidence_snippet": self._truncate_snippet(f"[{key}] {value}"),
                            "start_offset": None,
                            "end_offset": None,
                            "line_number": None,
                            "remediation": f"Clean or reset document metadata properties in '{key}'.",
                            "false_positive_note": "PDF/DOCX metadata is often automatically preserved from source templates."
                        })
        return findings

    # ─── Formatting & Presentation Helpers ───

    def _make_snippet_context(self, text: str, start: int, end: int, context_chars: int = 40) -> str:
        """
        Creates a safely truncated snippet with surrounding context and escaped control characters.
        """
        c_start = max(0, start - context_chars)
        c_end = min(len(text), end + context_chars)
        prefix = "..." if c_start > 0 else ""
        suffix = "..." if c_end < len(text) else ""

        match_text = text[start:end]
        raw_snippet = f"{prefix}{text[c_start:start]}>>>{match_text}<<<{text[end:c_end]}{suffix}"
        return self._sanitize_for_display(raw_snippet)

    def _make_character_evidence(self, text: str, offset: int, codepoint: str, char_name: str) -> str:
        """
        Constructs a safe visual snippet showing the position of an invisible character.
        """
        start = max(0, offset - 25)
        end = min(len(text), offset + 26)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""

        before = self._sanitize_for_display(text[start:offset])
        after = self._sanitize_for_display(text[offset + 1:end])
        return f"{prefix}{before}[{codepoint} {char_name}]{after}{suffix}"

    def _truncate_snippet(self, s: str, max_len: int = SECURITY_MAX_SNIPPET_LENGTH) -> str:
        sanitized = self._sanitize_for_display(s)
        if len(sanitized) > max_len:
            return sanitized[:max_len] + "..."
        return sanitized

    def _sanitize_for_display(self, text: str) -> str:
        """
        Replaces invisible control characters with readable markers and escapes HTML.
        Does NOT execute scripts or links.
        """
        if not text:
            return ""

        # Replace non-printable ASCII
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', lambda m: f"[0x{ord(m.group(0)):02X}]", text)
        
        # Replace zero-width and bidi characters with readable tags
        for char, meta in SECURITY_UNICODE_FORMAT_CHARS.items():
            if char in cleaned:
                cleaned = cleaned.replace(char, f"[{meta['codepoint']}]")

        # HTML escape to prevent XSS in web browser viewers
        escaped = html.escape(cleaned)
        return escaped

    def _generate_recommendations(
        self,
        critical_count: int,
        warning_count: int,
        hidden_summary: Dict[str, Any]
    ) -> List[str]:
        """
        Generates actionable, safe remediation advice based on findings.
        """
        recs = []
        if critical_count > 0:
            recs.append("Remove adversarial instruction phrasing (e.g. 'ignore previous instructions', 'give 100% score').")
            recs.append("Verify candidate qualifications through standard project deliverables rather than role commands.")
            recs.append("Do not pass unvetted resume text to unconstrained LLMs without boundary isolation.")

        if hidden_summary.get("bidi_overrides_detected", 0) > 0:
            recs.append("Eliminate bidirectional overrides (RLO/LRO) that alter visual text rendering order.")

        if hidden_summary.get("zero_width_detected", 0) > 0:
            recs.append("Remove zero-width format characters (U+200B, U+2060) unless required by Indic or Persian text.")

        if warning_count > 0 and critical_count == 0:
            recs.append("Review highlighted formatting notices to ensure resume displays consistently across ATS engines.")
            recs.append("Confirm that technical discussion of AI or prompt engineering is properly contextualized.")

        if not recs:
            recs.append("Document passed deterministic security checks. Continue with standard ATS matching.")
            recs.append("Maintain evidence-aware matching with verified project and experience deliverables.")

        return recs


# Singleton instance
security_service = SecurityAuditService()
