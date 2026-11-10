# AI Resume Builder & Deterministic ATS Analyzer

A Streamlit web application that combines **AI-powered resume generation** (Google Gemini) with a **deterministic ATS scoring engine** to help you build job-aligned resumes and audit them against any job description — with the same score every time.

## Features

### 📄 AI Resume Builder
- Enter your profile (name, title, contact, education, experience notes, skills)
- Paste a job description and let Gemini generate a tailored summary, achievement bullets, and categorized skills
- Live resume preview with clean, ATS-friendly styling
- Download the finished resume as a professionally formatted **PDF** (via ReportLab)
- Optional: generate a resume locally without AI (manual mode)

### 📊 ATS Score Analyzer
- Upload your resume as **PDF** or **DOCX** (text extraction via pdfplumber / python-docx)
- Paste the target job description
- Get a **deterministic 100-point audit**:
  | Component | Points | What it checks |
  |---|---|---|
  | Keyword alignment | 40 | JD keyword coverage (exact, partial, and stemmed matches) |
  | ATS structure | 30 | Standard section headers + email / phone / LinkedIn / GitHub / portfolio links |
  | Impact language | 30 | Quantified metrics (%, $, x, etc.) and strong action verbs |
- Detailed breakdown: matched, partial, and missing keywords, section checklist, metric and verb counts
- Actionable recommendations to improve your score

The scoring is fully rule-based (no AI), so the same resume + JD always produces the same score.

## Project Structure

```
├── app.py                    # Streamlit entry point
├── config.py                 # App constants, model options, regex patterns
├── models.py                 # TypedDict data models
├── utils.py                  # Shared helpers (text cleaning, URLs, skills)
├── ats_data.py               # Action verbs, section patterns, skill groups
├── requirements.txt
├── services/
│   ├── ai_service.py         # Gemini API calls + JSON response parsing
│   ├── ats_engine.py         # Deterministic ATS scoring engine
│   ├── pdf_service.py        # PDF resume generation (ReportLab)
│   └── resume_parser.py      # PDF / DOCX text extraction
└── ui/
    ├── builder_page.py      # Resume Builder page
    ├── analyzer_page.py     # ATS Analyzer page (score dashboard)
    ├── common.py            # Sidebar / shared UI
    ├── theme.py             # Theme injection
    └── styles.css           # Custom styling
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/panditmadhav6221/Ai-Resume-Builder-And-Analyzer.git
cd Ai-Resume-Builder-And-Analyzer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your Gemini API key

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
```

Or set it as an environment variable:

```bash
export GEMINI_API_KEY="your-gemini-api-key"   # Linux/macOS
set GEMINI_API_KEY=your-gemini-api-key         # Windows
```

Get a free key from [Google AI Studio](https://aistudio.google.com/apikey).

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Usage

1. **Build**: Open the *AI Resume Builder* page, fill in your details, paste the JD, choose a Gemini model, and generate → download the PDF.
2. **Analyze**: Open the *ATS Score Analyzer* page, upload the generated (or any existing) resume, paste the same JD, and run the audit to see your score and fixes.

## Tech Stack

- **Frontend/UI**: [Streamlit](https://streamlit.io/) with custom CSS theming
- **AI**: [Google Gemini](https://ai.google.dev/) (`google-genai` SDK)
- **PDF parsing**: [pdfplumber](https://github.com/jsvine/pdfplumber)
- **DOCX parsing**: [python-docx](https://python-docx.readthedocs.io/)
- **PDF generation**: [ReportLab](https://www.reportlab.com/)

## Notes

- Scanned/image-only PDFs are not supported — export a text-based PDF or upload a DOCX.
- Max upload size: 8 MB; max 40 PDF pages / 150k characters analyzed.
- The ATS score is a diagnostic signal, not a guarantee of any specific employer's ATS behavior.

## License

This project is for educational/personal use.
