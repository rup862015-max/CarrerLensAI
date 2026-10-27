"""
Dynamic Role & Job Generator Service for CareerLens AI
Synthesizes personalized, context-aware demo benchmark roles directly from the candidate's
provided resume, replacing static, hardcoded datasets.
Generates:
1. Target / Primary Alignment Role (Core Match)
2. Growth / Step-Up Role (Next Career Leap)
3. Adjacent / Specialization Pivot Role (Transferable Skills)
"""

import re
import uuid
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("careerlens.job_generator")

# In-memory LRU-style cache: resume_id -> list of DemoJob dicts
_ROLES_CACHE: Dict[str, List[Dict[str, Any]]] = {}


class JobGeneratorService:
    def __init__(self):
        pass

    def generate_roles_from_profile(
        self,
        resume_profile: Dict[str, Any],
        raw_text: str = "",
        resume_id: str = "custom"
    ) -> List[Dict[str, Any]]:
        """
        Dynamically generates 3 tailored benchmark roles customized to the candidate's
        domain, verified skills, experience level, and career trajectory.
        """
        if not resume_profile:
            return []

        # 1. Detect candidate's primary domain and current title
        domain, current_title = self._detect_domain_and_title(resume_profile, raw_text)
        years_exp = float(resume_profile.get("years_of_experience") or 0.0)
        skills = resume_profile.get("skills") or []
        experience_list = resume_profile.get("experience") or []

        # 2. Determine Seniority Level
        seniority = self._get_seniority(years_exp, current_title, raw_text)

        # 3. Build the 3 customized roles
        role_1 = self._build_target_role(domain, current_title, seniority, skills, years_exp, resume_id)
        role_2 = self._build_growth_role(domain, current_title, seniority, skills, years_exp, resume_id)
        role_3 = self._build_adjacent_role(domain, current_title, seniority, skills, years_exp, resume_id)

        roles = [role_1, role_2, role_3]
        _ROLES_CACHE[resume_id] = roles
        return roles

    def get_roles_for_resume(
        self,
        resume_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Resolves or dynamically generates roles for a specific resume or active user session.
        """
        from database import get_resume_by_id, get_latest_resume

        if resume_id and resume_id in _ROLES_CACHE:
            return _ROLES_CACHE[resume_id]

        record = None
        if resume_id:
            record = get_resume_by_id(resume_id, user_id=user_id)
        if not record:
            record = get_latest_resume(user_id=user_id)

        if not record or not record.get("extracted_profile"):
            return []

        res_id = record.get("resume_id") or record.get("id") or "resume"
        profile = record.get("extracted_profile") or {}
        raw_text = record.get("raw_text") or ""

        return self.generate_roles_from_profile(profile, raw_text=raw_text, resume_id=res_id)

    def get_job_by_id(
        self,
        job_id: str,
        resume_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Finds a specific demo job by ID among the dynamically generated roles.
        """
        roles = self.get_roles_for_resume(resume_id=resume_id, user_id=user_id)
        for r in roles:
            if r.get("id") == job_id:
                return r
        # If ID not found but roles exist, return first as safe fallback
        return roles[0] if roles else None

    # ─── Domain & Title Detection ───

    def _detect_domain_and_title(
        self,
        profile: Dict[str, Any],
        raw_text: str
    ) -> tuple[str, str]:
        """Detects whether candidate is in Finance, Software, Data/AI, Product, Marketing, Design, etc."""
        text_lower = raw_text.lower()
        skills_lower = [s.lower() for s in profile.get("skills", [])]
        experiences = profile.get("experience", [])

        # Check job titles in experience
        exp_titles = [e.get("title", "") for e in experiences if isinstance(e, dict) and e.get("title")]
        first_title = exp_titles[0] if exp_titles else ""

        # Check first 500 characters of resume for title banner (e.g. "FINANCIAL ANALYST | FP&A")
        header_snippet = raw_text[:500].lower()
        edu_text = " ".join([str(e) for e in profile.get("education", [])]).lower()
        unrec_text = " ".join([str(v) for v in (profile.get("unrecognized_sections") or {}).values()]).lower()
        combined_context = f"{header_snippet} {edu_text} {unrec_text}".lower()

        # Domain: Civil & Structural Engineering / Construction
        civil_keywords = [
            "civil engineer", "civil engineering", "structural engineer", "structural design",
            "site engineer", "autocad", "revit", "staad", "staad.pro", "boq", "quantity surveying",
            "quantity take-off", "quantity takeoff", "concrete", "construction management", "building study"
        ]
        if (
            any(k in combined_context for k in civil_keywords)
            or any(k in first_title.lower() for k in civil_keywords)
            or any(s in [
                "design tools: autocad", "autocad", "revit", "revit basics", "staad.pro",
                "staad.pro academic exposure", "boq preparation", "quantity take-off",
                "basic structural concepts", "concrete-work documentation", "measurement records"
            ] for s in skills_lower)
        ):
            title = first_title or ("Graduate Civil Engineer" if any(w in text_lower for w in ["fresher", "graduate", "trainee", "intern"]) or not experiences else "Civil & Structural Engineer")
            return "civil", title

        # Domain: Mechanical Engineering
        mech_keywords = ["mechanical engineer", "mechanical engineering", "solidworks", "catia", "ansys", "thermodynamics", "cad/cam", "hvac", "manufacturing engineer", "gd&t"]
        if (
            any(k in combined_context for k in mech_keywords)
            or any(k in first_title.lower() for k in mech_keywords)
            or any(s in ["solidworks", "catia", "ansys", "fea", "thermodynamics", "hvac", "gd&t"] for s in skills_lower)
        ):
            title = first_title or "Mechanical Design Engineer"
            return "mechanical", title

        # Domain: Electrical & Electronics Engineering
        elec_keywords = ["electrical engineer", "electronics engineer", "electrical engineering", "pcb", "embedded systems", "circuit design", "vlsi", "microcontroller", "plc"]
        if (
            any(k in combined_context for k in elec_keywords)
            or any(k in first_title.lower() for k in elec_keywords)
            or any(s in ["circuit design", "pcb design", "matlab", "embedded systems", "plc"] for s in skills_lower)
        ):
            title = first_title or "Electrical & Embedded Systems Engineer"
            return "electrical", title

        # Domain: Finance & Accounting
        finance_keywords = ["finance", "financial analyst", "fp&a", "accounting", "budgeting", "variance analysis", "auditing", "valuation"]
        if any(k in header_snippet for k in finance_keywords) or any(k in first_title.lower() for k in finance_keywords) or any(s in ["financial modeling", "fp&a", "budgeting", "variance analysis", "accounting"] for s in skills_lower):
            title = first_title or "Financial Analyst"
            if "fp&a" in header_snippet and "fp&a" not in title.lower():
                title = f"{title} (FP&A)"
            return "finance", title

        # Domain: Data Science / AI / Machine Learning
        ai_data_keywords = ["machine learning", "data scientist", "deep learning", "nlp", "llm", "ai engineer"]
        if any(k in header_snippet for k in ai_data_keywords) or any(k in first_title.lower() for k in ai_data_keywords) or any(s in ["machine learning", "deep learning", "nlp", "pytorch", "tensorflow"] for s in skills_lower):
            title = first_title or "Machine Learning Engineer"
            return "ai_data", title

        # Domain: Data Analytics & BI
        data_keywords = ["data analyst", "business intelligence", "bi analyst", "analytics", "tableau", "power bi"]
        if any(k in header_snippet for k in data_keywords) or any(k in first_title.lower() for k in data_keywords):
            title = first_title or "Data & Business Intelligence Analyst"
            return "data_analytics", title

        # Domain: Product Management
        pm_keywords = ["product manager", "product management", "technical product manager", "product owner"]
        if any(k in header_snippet for k in pm_keywords) or any(k in first_title.lower() for k in pm_keywords) or "product management" in skills_lower:
            title = first_title or "Product Manager"
            return "product", title

        # Domain: UI/UX & Design
        design_keywords = ["ui/ux", "product designer", "ux designer", "ui designer", "figma"]
        if any(k in header_snippet for k in design_keywords) or any(k in first_title.lower() for k in design_keywords) or "ui/ux design" in skills_lower:
            title = first_title or "Product Designer (UI/UX)"
            return "design", title

        # Domain: Marketing & Growth
        marketing_keywords = ["marketing", "seo", "growth", "content strategist", "digital marketing"]
        if any(k in header_snippet for k in marketing_keywords) or any(k in first_title.lower() for k in marketing_keywords) or "seo" in skills_lower:
            title = first_title or "Digital Marketing & Growth Specialist"
            return "marketing", title

        # Domain: Frontend Engineering
        frontend_keywords = ["frontend", "front end", "react", "vue", "angular", "ui engineer"]
        if any(k in header_snippet for k in frontend_keywords) or any(k in first_title.lower() for k in frontend_keywords) or any(s in ["react", "vue.js", "angular", "typescript", "tailwind css"] for s in skills_lower):
            title = first_title or "Frontend Engineer"
            return "frontend", title

        # Domain: DevOps & Cloud
        devops_keywords = ["devops", "cloud engineer", "sre", "site reliability", "infrastructure", "kubernetes", "aws"]
        if any(k in header_snippet for k in devops_keywords) or any(k in first_title.lower() for k in devops_keywords) or any(s in ["docker", "kubernetes", "terraform", "aws", "azure"] for s in skills_lower):
            title = first_title or "DevOps & Cloud Engineer"
            return "devops", title

        # Domain: Software / Backend Engineering (Default Tech)
        title = first_title or "Software Engineer"
        return "backend", title

    def _get_seniority(self, years_exp: float, title: str, raw_text: str) -> str:
        """Determines candidate seniority tier."""
        lower = (title + " " + raw_text[:400]).lower()
        if any(w in lower for w in ["lead", "staff", "principal", "director", "head of", "architect"]) or years_exp >= 8:
            return "Lead / Staff"
        if any(w in lower for w in ["senior", "sr."]) or years_exp >= 5:
            return "Senior"
        if years_exp >= 2 or any(w in lower for w in ["mid", "experienced", "intermediate"]):
            return "Mid-Level"
        return "Junior / Associate"

    # ─── Role Builders ───

    def _build_target_role(
        self,
        domain: str,
        current_title: str,
        seniority: str,
        skills: List[str],
        years_exp: float,
        resume_id: str
    ) -> Dict[str, Any]:
        """Generates Role 1: Direct Target / Core Match."""
        role_id = f"role-{resume_id[:8]}-target"
        clean_title = self._clean_role_title(current_title, domain, seniority)

        if domain == "finance":
            department = "Corporate Finance & Strategy"
            desc = (
                f"We are seeking an analytical {clean_title} to steer financial modeling, variance reporting, "
                f"and strategic budgeting. You will partner with business unit leaders to monitor operating performance, "
                f"distinguish actuals from forecasts, and build automated reporting pipelines."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Financial Modeling", "FP&A", "Excel", "SQL", "Variance Analysis", "Budgeting", "Power BI", "Financial Reporting"],
                category_map={"Excel": "ai_data", "SQL": "databases", "Power BI": "ai_data", "Tableau": "ai_data"}
            )
            edu = "Bachelor's degree in Finance, Accounting, Economics, or related quantitative field"
            resps = [
                "Develop and maintain dynamic three-statement financial models, forecasts, and operating budgets.",
                "Conduct monthly variance analysis comparing actual financial results against budgeted targets.",
                "Build interactive executive dashboards in Power BI and Excel to track corporate KPIs.",
                "Query financial databases using SQL to audit data quality and reconcile general ledger actuals.",
                "Partner with leadership to provide actionable financial recommendations for cost optimization."
            ]

        elif domain == "frontend":
            department = "UI/UX Engineering"
            desc = (
                f"Looking for a skilled {clean_title} passionate about engineering fast, accessible, and responsive "
                f"web applications. You will collaborate with product designers and backend teams to deliver modular component architectures."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["React", "TypeScript", "JavaScript", "HTML", "CSS", "Tailwind CSS", "REST APIs", "Git"],
                category_map={"React": "frameworks", "TypeScript": "languages", "Git": "practices"}
            )
            edu = "Bachelor's degree in Computer Science, Software Engineering, or equivalent practical experience"
            resps = [
                "Architect and implement reusable, accessible frontend components in React and TypeScript.",
                "Collaborate with product designers in Figma to translate wireframes into interactive user experiences.",
                "Integrate client-side applications with RESTful APIs, handling asynchronous state efficiently.",
                "Optimize web vitals, bundle sizes, and cross-browser responsiveness.",
                "Write automated component unit tests and participate in code reviews."
            ]

        elif domain == "ai_data":
            department = "Machine Learning & AI Research"
            desc = (
                f"Seeking an innovative {clean_title} to develop, train, and deploy predictive models and AI solutions. "
                f"You will work closely with data engineering to optimize feature pipelines and scale model inference."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Python", "Machine Learning", "Deep Learning", "PyTorch", "SQL", "Pandas", "Scikit-Learn", "Git"],
                category_map={"Python": "languages", "SQL": "databases", "PyTorch": "ai_data"}
            )
            edu = "Degree in Computer Science, Data Science, Artificial Intelligence, or Mathematics"
            resps = [
                "Design, train, and validate supervised and unsupervised machine learning models.",
                "Engineer scalable feature pipelines using Python, Pandas, and SQL.",
                "Deploy production-grade model inference services via RESTful APIs.",
                "Evaluate model performance, drift, and fairness metrics against benchmark datasets.",
                "Collaborate with engineering squads to integrate AI capabilities into production products."
            ]

        elif domain == "data_analytics":
            department = "Business Intelligence & Analytics"
            desc = (
                f"We are hiring a detail-oriented {clean_title} to turn complex multi-source datasets into actionable "
                f"business intelligence, automated executive dashboards, and strategic growth insights."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SQL", "Power BI", "Tableau", "Excel", "Data Visualization", "Python", "Pandas"],
                category_map={"SQL": "databases", "Power BI": "ai_data", "Tableau": "ai_data"}
            )
            edu = "Bachelor's degree in Business Analytics, Statistics, Information Systems, or related field"
            resps = [
                "Write optimized SQL queries and transformation scripts across enterprise data warehouses.",
                "Design and maintain interactive Power BI and Tableau dashboards for leadership.",
                "Perform exploratory data analysis to identify operational trends and anomalies.",
                "Automate weekly and monthly KPI reporting pipelines to reduce manual turnaround.",
                "Communicate analytical findings clearly to non-technical business partners."
            ]

        elif domain == "product":
            department = "Product Strategy & Management"
            desc = (
                f"Seeking an impactful {clean_title} to drive customer-centric product discovery, backlog prioritization, "
                f"and cross-functional delivery from concept to launch."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Product Management", "Agile", "Jira", "User Stories", "Roadmapping", "A/B Testing", "Stakeholder Management"],
                category_map={"Jira": "product_management", "Agile": "practices"}
            )
            edu = "Bachelor's degree in Business, Computer Science, or equivalent experience"
            resps = [
                "Define and communicate product strategy, vision, and quarterly roadmap milestones.",
                "Write detailed user stories, PRDs, and acceptance criteria in Jira.",
                "Lead cross-functional squads through Agile sprint planning and retrospective ceremonies.",
                "Analyze user engagement metrics and A/B test results to iterate on core features."
            ]

        elif domain == "marketing":
            department = "Growth & Digital Marketing"
            desc = (
                f"Seeking a data-driven {clean_title} to accelerate customer acquisition, content marketing, "
                f"and campaign optimization across organic and paid channels."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SEO", "SEM", "Google Analytics", "Content Strategy", "CRM", "Copywriting", "A/B Testing"],
                category_map={"SEO": "marketing", "Google Analytics": "marketing"}
            )
            edu = "Bachelor's degree in Marketing, Communications, Business, or related field"
            resps = [
                "Plan and execute data-driven digital marketing campaigns across SEO, content, and paid search.",
                "Track and analyze web traffic, conversions, and customer funnels in Google Analytics.",
                "Conduct A/B testing on landing pages and ad copy to maximize ROI.",
                "Collaborate with product and sales teams to align lead generation strategies."
            ]

        elif domain == "design":
            department = "Product Design & Experience"
            desc = (
                f"Looking for a creative {clean_title} to craft intuitive, accessible, and delightful product experiences. "
                f"You will lead user research, wireframing, and interactive prototyping."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["UI/UX Design", "Figma", "User Research", "Design Systems", "Prototyping", "Wireframing"],
                category_map={"Figma": "design", "UI/UX Design": "design"}
            )
            edu = "Degree or portfolio equivalent in HCI, Graphic Design, or Product Design"
            resps = [
                "Design end-to-end user flows, interactive prototypes, and wireframes in Figma.",
                "Conduct qualitative user interviews and usability testing sessions.",
                "Evolve and maintain our design system components for engineering handoff."
            ]

        elif domain == "civil":
            department = "Civil & Structural Engineering"
            desc = (
                f"We are hiring a dedicated {clean_title} to support structural drafting, site measurement documentation, "
                f"and quantity take-offs. You will work with project engineers to coordinate floor plans, "
                f"verify concrete quality logs, and ensure building code compliance."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["AutoCAD", "Revit", "STAAD.Pro", "Basic Structural Concepts", "BOQ Preparation", "Quantity Take-Off", "Concrete-Work Documentation", "Measurement Records", "Safety Awareness", "Technical Report Writing", "Excel"],
                category_map={
                    "AutoCAD": "civil_engineering",
                    "Revit": "civil_engineering",
                    "STAAD.Pro": "civil_engineering",
                    "Basic Structural Concepts": "civil_engineering",
                    "BOQ Preparation": "civil_engineering",
                    "Quantity Take-Off": "civil_engineering",
                    "Concrete-Work Documentation": "civil_engineering",
                    "Measurement Records": "civil_engineering",
                    "Safety Awareness": "civil_engineering",
                    "Technical Report Writing": "civil_engineering",
                    "Excel": "ai_data"
                }
            )
            edu = "Bachelor's degree or Diploma in Civil Engineering, Structural Engineering, or Construction Technology"
            resps = [
                "Prepare and verify detailed 2D/3D structural drawings using AutoCAD and Revit.",
                "Perform basic structural checks and load calculation models using STAAD.Pro.",
                "Prepare accurate quantity take-offs and compile Bills of Quantities (BOQ).",
                "Maintain concrete-work inspection records, slump/cube test documentation, and site logs.",
                "Ensure compliance with municipal building codes and safety regulations."
            ]

        elif domain == "mechanical":
            department = "Mechanical Design & Engineering"
            desc = (
                f"Seeking a talented {clean_title} to develop 3D CAD models, evaluate thermal/structural simulations, "
                f"and coordinate prototyping with manufacturing teams."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SolidWorks", "CATIA", "ANSYS", "Finite Element Analysis", "Thermodynamics", "HVAC", "GD&T"],
                category_map={"SolidWorks": "mechanical_engineering", "ANSYS": "mechanical_engineering"}
            )
            edu = "Bachelor's degree in Mechanical Engineering or related field"
            resps = [
                "Create parametric 3D models and manufacturing drawings in SolidWorks/CATIA.",
                "Perform finite element analysis (FEA) and thermal simulations using ANSYS.",
                "Apply GD&T standards to component specifications and inspect production prototypes."
            ]

        elif domain == "electrical":
            department = "Electrical & Embedded Systems"
            desc = (
                f"Looking for an {clean_title} to design schematics, layout printed circuit boards, "
                f"and develop firmware for embedded hardware platforms."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Circuit Design", "PCB Design", "Embedded Systems", "MATLAB", "PLC"],
                category_map={"PCB Design": "electrical_engineering", "MATLAB": "electrical_engineering"}
            )
            edu = "Bachelor's degree in Electrical Engineering, Electronics, or Computer Engineering"
            resps = [
                "Design schematic diagrams and multi-layer PCB layouts.",
                "Program and debug microcontrollers and embedded firmware.",
                "Perform circuit simulations and validation testing using MATLAB."
            ]

        else: # Default backend / software engineering
            department = "Platform & Backend Engineering"
            desc = (
                f"We are looking for a capable {clean_title} to build, scale, and maintain high-throughput backend services "
                f"and RESTful APIs. You will collaborate with product squads to deliver reliable cloud-native microservices."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Python", "REST APIs", "SQL", "PostgreSQL", "Docker", "Git", "Microservices", "Linux"],
                category_map={"Python": "languages", "SQL": "databases", "Docker": "cloud_devops"}
            )
            edu = "Bachelor's degree in Computer Science, Software Engineering, or related technical discipline"
            resps = [
                "Architect and deploy scalable server-side REST APIs and microservices.",
                "Design robust relational database schemas and optimize query performance in PostgreSQL.",
                "Containerize services with Docker and manage deployment pipelines.",
                "Ensure application reliability through unit testing, observability, and code reviews."
            ]

        exp_range = f"{max(1, int(years_exp))}-{max(3, int(years_exp + 2))} years"

        return {
            "id": role_id,
            "title": clean_title,
            "department": department,
            "location": "Remote / Hybrid (Flexible)",
            "experience_level": f"{seniority} ({exp_range})",
            "description": desc,
            "requirements": reqs,
            "education_requirement": edu,
            "responsibilities": resps
        }

    def _build_growth_role(
        self,
        domain: str,
        current_title: str,
        seniority: str,
        skills: List[str],
        years_exp: float,
        resume_id: str
    ) -> Dict[str, Any]:
        """Generates Role 2: Growth / Step-Up Role (Next Career Leap)."""
        role_id = f"role-{resume_id[:8]}-growth"
        higher_seniority = "Senior" if "Junior" in seniority or "Mid" in seniority else "Lead / Principal"

        if domain == "finance":
            title = f"{higher_seniority} FP&A Analyst & Strategic Finance Partner"
            department = "Strategic Planning & Executive Finance"
            desc = (
                f"Seeking a high-impact {title} to lead long-range strategic financial planning, "
                f"capital allocation models, and scenario forecasting. You will serve as the primary finance partner to C-suite leadership."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Financial Modeling", "FP&A", "Forecasting", "Budgeting", "SQL", "Power BI", "Accounting", "Variance Analysis", "Financial Reporting"],
                category_map={"SQL": "databases", "Power BI": "ai_data"}
            )
            resps = [
                "Lead annual budgeting and multi-year strategic financial planning cycles.",
                "Architect complex scenario and sensitivity models to evaluate corporate investments and M&A opportunities.",
                "Present quarterly business reviews and financial forecasts directly to executive leadership.",
                "Drive finance automation by integrating BI dashboards with enterprise ERP and accounting records.",
                "Mentor junior finance analysts and champion corporate financial governance."
            ]

        elif domain == "frontend":
            title = f"{higher_seniority} Frontend & UI Architecture Engineer"
            department = "Core Web Architecture"
            desc = (
                f"We are hiring a {title} to spearhead our design system architecture, state orchestration, "
                f"and next-generation client-side performance."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["React", "TypeScript", "Next.js", "Redux", "Tailwind CSS", "System Design", "REST APIs", "CI/CD"],
                category_map={"Next.js": "frameworks", "CI/CD": "cloud_devops"}
            )
            resps = [
                "Architect scalable frontend infrastructure and shared component design systems.",
                "Establish performance standards, bundle size limits, and web vital benchmarks.",
                "Mentor frontend engineers across squads through rigorous architecture reviews.",
                "Pioneer modern SSR/SSG patterns using Next.js and React Server Components."
            ]

        elif domain in ["ai_data", "data_analytics"]:
            title = f"{higher_seniority} Analytics & Machine Learning Lead"
            department = "Enterprise Data & AI Strategy"
            desc = (
                f"Looking for a {title} to guide data modeling strategy, production ML workflows, "
                f"and executive analytics infrastructure."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Python", "SQL", "Machine Learning", "Power BI", "Snowflake", "Docker", "Data Visualization", "Git"],
                category_map={"Snowflake": "databases", "Docker": "cloud_devops"}
            )
            resps = [
                "Lead cross-functional data initiatives transforming raw enterprise events into strategic intelligence.",
                "Architect production ML pipelines and automated data quality validation frameworks.",
                "Advise executive stakeholders on data architecture, privacy standards, and AI integration."
            ]

        elif domain == "marketing":
            title = f"{higher_seniority} Growth Marketing & Demand Generation Lead"
            department = "Strategic Marketing & Acquisition"
            desc = (
                f"Seeking a strategic {title} to direct omnichannel growth initiatives, performance marketing, "
                f"and full-funnel attribution models."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SEO", "SEM", "Google Analytics", "Content Strategy", "A/B Testing", "CRM", "Product Management"],
                category_map={"SEO": "marketing", "Google Analytics": "marketing"}
            )
            resps = [
                "Lead quarterly growth marketing strategy and customer acquisition budgets.",
                "Design full-funnel conversion attribution models in Google Analytics.",
                "Direct marketing agency partners and scale organic and paid growth."
            ]

        elif domain == "product":
            title = f"{higher_seniority} Group Product Manager & Platform Lead"
            department = "Executive Product Management"
            desc = (
                f"Hiring a visionary {title} to orchestrate portfolio roadmaps, cross-functional squad alignment, "
                f"and strategic product discovery."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Product Management", "Roadmapping", "User Stories", "Stakeholder Management", "Agile", "A/B Testing", "Jira"],
                category_map={"Product Management": "product_management", "Jira": "product_management"}
            )
            resps = [
                "Define enterprise product portfolio strategy and multi-year investment roadmaps.",
                "Lead executive stakeholder alignment ceremonies and quarterly business reviews.",
                "Mentor product managers across core squads."
            ]

        elif domain == "civil":
            title = f"{higher_seniority} Structural Project Engineer & Project Lead"
            department = "Project Engineering & Construction Management"
            desc = (
                f"We are hiring a {title} to oversee structural design execution, cross-discipline BIM coordination, "
                f"and large-scale construction project deliverables."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["STAAD.Pro", "Revit", "AutoCAD", "Basic Structural Concepts", "BOQ Preparation", "Scheduling Basics", "Concrete-Work Documentation", "Technical Report Writing", "Safety Awareness", "Excel"],
                category_map={
                    "STAAD.Pro": "civil_engineering",
                    "Revit": "civil_engineering",
                    "AutoCAD": "civil_engineering",
                    "Basic Structural Concepts": "civil_engineering",
                    "BOQ Preparation": "civil_engineering",
                    "Scheduling Basics": "civil_engineering",
                    "Concrete-Work Documentation": "civil_engineering"
                }
            )
            resps = [
                "Lead structural design sign-offs and ensure compliance with building codes and standards.",
                "Coordinate multidisciplinary BIM models across architectural and structural engineering squads in Revit.",
                "Oversee project schedules, contractor BOQs, and material procurement pipelines.",
                "Mentor site engineers on structural concrete quality assurance, safety audits, and contract documentation."
            ]

        elif domain == "mechanical":
            title = f"{higher_seniority} Mechanical Systems & Simulation Architect"
            department = "Advanced Mechanical Engineering"
            desc = (
                f"Seeking an experienced {title} to direct mechanical system architecture, complex FEA simulations, "
                f"and product lifecycle management."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SolidWorks", "ANSYS", "Finite Element Analysis", "CATIA", "Thermodynamics", "GD&T"],
                category_map={"ANSYS": "mechanical_engineering", "SolidWorks": "mechanical_engineering"}
            )
            resps = [
                "Direct mechanical system architecture and engineering sign-offs.",
                "Perform complex FEA and thermal simulations on critical product assemblies.",
                "Lead cross-functional reviews with manufacturing and tooling vendors."
            ]

        elif domain == "electrical":
            title = f"{higher_seniority} Hardware Systems & Power Architecture Lead"
            department = "Hardware Engineering Leadership"
            desc = (
                f"Looking for a {title} to guide embedded hardware architecture, power distribution design, "
                f"and compliance certifications."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Circuit Design", "PCB Design", "Embedded Systems", "MATLAB", "PLC"],
                category_map={"PCB Design": "electrical_engineering", "Embedded Systems": "electrical_engineering"}
            )
            resps = [
                "Architect multi-board embedded systems and high-speed PCB layouts.",
                "Define testing strategies for electromagnetic compatibility (EMC) and reliability.",
                "Guide junior hardware and firmware engineers."
            ]

        else:
            title = f"{higher_seniority} Distributed Systems & Cloud Architect"
            department = "Platform Architecture"
            desc = (
                f"Seeking a {title} to design fault-tolerant microservices, cloud infrastructure, "
                f"and automated CI/CD deployment pipelines."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Python", "Microservices", "System Design", "Docker", "Kubernetes", "AWS", "SQL", "PostgreSQL"],
                category_map={"Kubernetes": "cloud_devops", "System Design": "practices"}
            )
            resps = [
                "Design resilient, high-throughput distributed microservice architectures.",
                "Guide cloud migration and container orchestration using Kubernetes and AWS.",
                "Establish engineering best practices for API security, caching, and database scaling."
            ]

        exp_range = f"{max(3, int(years_exp + 2))}-{max(6, int(years_exp + 5))} years"

        return {
            "id": role_id,
            "title": title,
            "department": department,
            "location": "Remote / Hybrid",
            "experience_level": f"{higher_seniority} ({exp_range})",
            "description": desc,
            "requirements": reqs,
            "education_requirement": "Bachelor's or Master's degree in relevant discipline",
            "responsibilities": resps
        }

    def _build_adjacent_role(
        self,
        domain: str,
        current_title: str,
        seniority: str,
        skills: List[str],
        years_exp: float,
        resume_id: str
    ) -> Dict[str, Any]:
        """Generates Role 3: Adjacent / Specialization Pivot (Transferable Skills)."""
        role_id = f"role-{resume_id[:8]}-adjacent"

        if domain == "finance":
            title = "Financial Data & Business Intelligence Specialist"
            department = "Finance Operations & Analytics"
            desc = (
                f"Seeking a hybrid {title} to bridge the gap between finance accounting and data engineering. "
                f"You will leverage SQL, Power BI, and financial modeling to automate reporting and uncover business drivers."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SQL", "Power BI", "Tableau", "Excel", "Financial Modeling", "FP&A", "Variance Analysis", "Data Visualization"],
                category_map={"SQL": "databases", "Power BI": "ai_data", "Tableau": "ai_data"}
            )
            resps = [
                "Build automated ETL queries and data pipelines connecting accounting ERPs to Power BI dashboards.",
                "Design enterprise data models to eliminate manual spreadsheet reconciliation.",
                "Partner with accounting and operations to audit data fidelity and financial audit trails.",
                "Train finance business partners on self-service business intelligence reporting."
            ]

        elif domain == "frontend":
            title = "Full-Stack Web & Cloud Developer"
            department = "Product Engineering"
            desc = (
                f"Opportunity for a frontend engineer to expand into full-stack engineering, "
                f"building robust Node.js/Python backend APIs alongside modern React frontends."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["React", "TypeScript", "Node.js", "Express", "SQL", "PostgreSQL", "REST APIs", "Docker"],
                category_map={"Node.js": "frameworks", "PostgreSQL": "databases"}
            )
            resps = [
                "Build end-to-end features spanning React web clients and backend Node.js microservices.",
                "Design database schemas and optimize RESTful endpoints for frontend consumption.",
                "Participate in full deployment lifecycles using Docker and cloud infrastructure."
            ]

        elif domain in ["ai_data", "data_analytics"]:
            title = "MLOps & Data Platform Engineer"
            department = "Platform Engineering"
            desc = (
                f"Focus on the infrastructure side of data: automating model deployments, "
                f"monitoring pipeline latency, and managing cloud data warehouses."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Python", "SQL", "Docker", "AWS", "CI/CD", "Machine Learning", "Linux", "Git"],
                category_map={"Docker": "cloud_devops", "AWS": "cloud_devops"}
            )
            resps = [
                "Deploy machine learning models into containerized Kubernetes and Docker microservices.",
                "Maintain automated data ingestion pipelines and feature store architectures.",
                "Monitor production inference latency, drift metrics, and system uptime."
            ]

        elif domain == "marketing":
            title = "Marketing Analytics & Growth Operations Specialist"
            department = "Marketing Operations & Analytics"
            desc = (
                f"Bridge marketing and data analytics by managing full-funnel tracking, "
                f"lead enrichment pipelines, and marketing automation systems."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Google Analytics", "SQL", "CRM", "SEO", "A/B Testing", "Excel", "Content Strategy"],
                category_map={"Google Analytics": "marketing", "SQL": "databases", "Excel": "ai_data"}
            )
            resps = [
                "Build marketing attribution models and executive performance dashboards.",
                "Integrate CRM and marketing automation platforms to track conversion lifecycles.",
                "Analyze organic and paid performance to optimize marketing spend."
            ]

        elif domain == "product":
            title = "Product Analytics & Strategy Operations Manager"
            department = "Product Operations"
            desc = (
                f"Partner with product managers and executive leadership to track feature adoption, "
                f"quantify user friction, and guide data-informed product discovery."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Product Management", "A/B Testing", "SQL", "Jira", "User Stories", "Roadmapping"],
                category_map={"SQL": "databases", "Product Management": "product_management"}
            )
            resps = [
                "Analyze user retention, churn, and feature engagement funnels.",
                "Design and monitor product experiments and A/B test variants.",
                "Synthesize qualitative feedback and quantitative metrics for executive product reviews."
            ]

        elif domain == "civil":
            title = "BIM Coordinator & Digital Construction Specialist"
            department = "Digital Engineering & Virtual Construction"
            desc = (
                f"Bridge physical site execution and digital architecture by leveraging 3D BIM models, "
                f"clash detection workflows, and automated quantity estimation."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Revit", "AutoCAD", "Quantity Take-Off", "BOQ Preparation", "Scheduling Basics", "Basic Structural Concepts", "Excel", "Technical Report Writing"],
                category_map={
                    "Revit": "civil_engineering",
                    "AutoCAD": "civil_engineering",
                    "Quantity Take-Off": "civil_engineering",
                    "BOQ Preparation": "civil_engineering",
                    "Scheduling Basics": "civil_engineering",
                    "Excel": "ai_data"
                }
            )
            resps = [
                "Build and coordinate 3D BIM models in Revit for clash detection and constructability reviews.",
                "Extract automated quantity take-offs directly from parametric BIM schedules.",
                "Facilitate digital handover packages and technical drawings for client consultants and project managers."
            ]

        elif domain == "mechanical":
            title = "Manufacturing Automation & Quality Engineer"
            department = "Manufacturing & Operations"
            desc = (
                f"Optimize manufacturing operations, automated inspection tooling, and quality assurance processes."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["SolidWorks", "GD&T", "ANSYS", "Finite Element Analysis"],
                category_map={"SolidWorks": "mechanical_engineering"}
            )
            resps = [
                "Design automated inspection fixtures and tooling in SolidWorks.",
                "Establish quality control standards and GD&T tolerance checks."
            ]

        elif domain == "electrical":
            title = "IoT & Firmware Integration Specialist"
            department = "Connected Systems & IoT"
            desc = (
                f"Integrate sensors, microcontrollers, and wireless communications into connected smart devices."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Embedded Systems", "Circuit Design", "PCB Design", "MATLAB"],
                category_map={"Embedded Systems": "electrical_engineering"}
            )
            resps = [
                "Develop embedded firmware for connected IoT devices and sensor arrays.",
                "Validate wireless hardware interfaces and low-power circuit operation."
            ]

        else: # Software -> DevOps / Cloud Infrastructure
            title = "Cloud Infrastructure & DevOps Engineer"
            department = "Cloud Platform Engineering"
            desc = (
                f"Leverage your software engineering background to build automated infrastructure, "
                f"CI/CD deployment systems, and containerized cloud platforms."
            )
            reqs = self._select_requirements(
                core_candidates=skills,
                domain_essentials=["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD", "Python", "Linux", "Git"],
                category_map={"Terraform": "cloud_devops", "Kubernetes": "cloud_devops"}
            )
            resps = [
                "Automate infrastructure provisioning using Terraform and AWS cloud services.",
                "Design and maintain scalable Kubernetes container clusters.",
                "Build automated GitHub Actions CI/CD release pipelines for engineering squads."
            ]

        exp_range = f"{max(2, int(years_exp))}-{max(4, int(years_exp + 3))} years"

        return {
            "id": role_id,
            "title": title,
            "department": department,
            "location": "Remote / Hybrid",
            "experience_level": f"{seniority} ({exp_range})",
            "description": desc,
            "requirements": reqs,
            "education_requirement": "Bachelor's degree in quantitative or engineering field",
            "responsibilities": resps
        }

    # ─── Requirement Alignment Helper ───

    def _select_requirements(
        self,
        core_candidates: List[str],
        domain_essentials: List[str],
        category_map: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """
        Synthesizes a realistic requirement set combining candidate's existing strengths
        with standard domain expectations and growth skills.
        """
        requirements = []
        seen = set()

        # 1. Add candidate's matching skills first (to ensure fair baseline match)
        for s in core_candidates:
            s_clean = s.strip()
            if s_clean.lower() in seen or len(s_clean) < 2:
                continue
            # Match if it appears in domain essentials
            matched_essential = next((de for de in domain_essentials if de.lower() == s_clean.lower()), None)
            if matched_essential:
                seen.add(s_clean.lower())
                cat = category_map.get(matched_essential, "general")
                requirements.append({
                    "name": matched_essential,
                    "importance": "critical",
                    "category": cat
                })

        # 2. Add domain essentials that candidate may be missing (creating actionable gap)
        for de in domain_essentials:
            if de.lower() not in seen:
                seen.add(de.lower())
                cat = category_map.get(de, "general")
                importance = "critical" if len(requirements) < 4 else "recommended"
                requirements.append({
                    "name": de,
                    "importance": importance,
                    "category": cat
                })

        # Ensure at least 6-8 requirements
        return requirements[:10]

    def _clean_role_title(self, raw_title: str, domain: str, seniority: str) -> str:
        """Sanitizes raw title and ensures seniority prefix is sensible."""
        if not raw_title or len(raw_title) < 4:
            defaults = {
                "finance": "Financial Analyst",
                "civil": "Civil & Structural Engineer",
                "mechanical": "Mechanical Design Engineer",
                "electrical": "Electrical & Systems Engineer",
                "frontend": "Frontend Engineer",
                "ai_data": "Machine Learning Engineer",
                "data_analytics": "Data & BI Analyst",
                "product": "Product Manager",
                "design": "Product Designer (UI/UX)",
                "marketing": "Digital Marketing Specialist",
                "backend": "Software Engineer"
            }
            raw_title = defaults.get(domain, "Software Engineer")

        # Strip pipes or trailing tags
        cleaned = re.split(r'[|\-,]', raw_title)[0].strip()

        # Add seniority prefix if not already present
        if seniority and seniority not in ["Mid-Level", "General"] and seniority.split()[0].lower() not in cleaned.lower():
            return f"{seniority} {cleaned}"
        return cleaned


# Global Singleton
job_generator_service = JobGeneratorService()
