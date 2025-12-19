CREATE TABLE public.Company (
  company_id integer NOT NULL DEFAULT nextval('"Company_company_id_seq"'::regclass),
  name character varying NOT NULL UNIQUE,
  industry character varying,
  interests character varying,
  CONSTRAINT Company_pkey PRIMARY KEY (company_id)
);
CREATE TABLE public.CompanyInterest (
  company_id integer NOT NULL,
  paper_id integer NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT CompanyInterest_pkey PRIMARY KEY (company_id, paper_id),
  CONSTRAINT CompanyInterest_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.Company(company_id),
  CONSTRAINT CompanyInterest_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.Paper(paper_id)
);
CREATE TABLE public.Complaint (
  complaint_id integer NOT NULL DEFAULT nextval('"Complaint_complaint_id_seq"'::regclass),
  paper_id integer NOT NULL,
  reporter_name character varying,
  reporter_email character varying,
  category character varying NOT NULL DEFAULT 'General'::character varying,
  description text NOT NULL,
  created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT Complaint_pkey PRIMARY KEY (complaint_id),
  CONSTRAINT Complaint_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.Paper(paper_id)
);
CREATE TABLE public.Paper (
  paper_id integer NOT NULL DEFAULT nextval('"Paper_paper_id_seq"'::regclass),
  user_id integer NOT NULL,
  title character varying NOT NULL,
  abstract text NOT NULL,
  upload_date timestamp without time zone DEFAULT now(),
  file_path character varying NOT NULL,
  research_domain character varying NOT NULL,
  ai_business_score integer,
  ai_academic_score integer,
  ai_summary text,
  ai_strengths text,
  ai_weaknesses text,
  ai_status character varying,
  CONSTRAINT Paper_pkey PRIMARY KEY (paper_id),
  CONSTRAINT Paper_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.User(user_id)
);
CREATE TABLE public.PaperCompany (
  paper_id integer NOT NULL,
  company_id integer NOT NULL,
  CONSTRAINT PaperCompany_pkey PRIMARY KEY (paper_id, company_id),
  CONSTRAINT PaperCompany_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.Company(company_id),
  CONSTRAINT PaperCompany_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.Paper(paper_id)
);
CREATE TABLE public.Review (
  review_id integer NOT NULL DEFAULT nextval('"Review_review_id_seq"'::regclass),
  paper_id integer NOT NULL,
  reviewer_id integer NOT NULL,
  score double precision,
  comments text,
  date_submitted timestamp without time zone DEFAULT now(),
  company_id integer,
  CONSTRAINT Review_pkey PRIMARY KEY (review_id),
  CONSTRAINT Review_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.Paper(paper_id),
  CONSTRAINT Review_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.Company(company_id),
  CONSTRAINT Review_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.User(user_id)
);
CREATE TABLE public.User (
  user_id integer NOT NULL DEFAULT nextval('"User_user_id_seq"'::regclass),
  name character varying NOT NULL,
  email character varying NOT NULL UNIQUE,
  role character varying NOT NULL CHECK (role::text = ANY (ARRAY['Researcher'::character varying::text, 'Reviewer'::character varying::text, 'Company'::character varying::text, 'User'::character varying::text, 'System/Admin'::character varying::text, 'Founder'::character varying::text])),
  preferences json,
  CONSTRAINT User_pkey PRIMARY KEY (user_id)
);
CREATE TABLE public.alembic_version (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num)
);