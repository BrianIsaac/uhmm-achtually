# Reverse Engineering Playground - Architecture Design

> **Cursor Singapore 24-Hour Hackathon Project**
> Using AI to reconstruct source code from compiled binaries

---

## 🎯 Project Overview

**Reverse Engineering Playground** is a web-based tool that uses multiple AI models to analyze compiled binaries and reconstruct their original source code. Users upload an executable file, and the system provides:

1. **Assembly disassembly** (via Gemini Vision)
2. **Pseudo-code reconstruction** (via Claude)
3. **Fast pattern analysis & exploit detection** (via Groq)

### Key Features
- 🔍 Multi-AI binary analysis pipeline
- 📊 Side-by-side comparison: Assembly → Pseudo-code → AI Insights
- 🔓 Automatic password/secret extraction
- 🐛 Vulnerability detection
- 🎯 Keygen generation for license validation
- 💾 Analysis history storage with Supabase

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React/Vue + TailwindCSS)                    │
├─────────────────────────────────────────────────────────────────┤
│  📤 Binary Upload  │  📊 Analysis View  │  💾 History         │
└──────────┬──────────────────────┬───────────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│   BACKEND API        │  │        SUPABASE DATABASE             │
│  (FastAPI/Express)   │◄─┤  - Analysis history                  │
└──────────┬───────────┘  │  - User sessions                     │
           │              │  - Binary metadata                   │
           ▼              └──────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│              BINARY ANALYSIS PIPELINE (Backend)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Disassembly                                            │
│  ┌─────────────────────────────────────────────────┐            │
│  │ Radare2 / Capstone Engine                       │            │
│  │ - Extracts assembly instructions                │            │
│  │ - Identifies functions & control flow           │            │
│  │ - Finds hardcoded strings                       │            │
│  └─────────────┬───────────────────────────────────┘            │
│                │                                                │
│                ▼                                                │
│  Step 2: Multi-AI Analysis (Parallel)                           │
│  ┌─────────────┬────────────────┬──────────────────┐            │
│  │             │                │                  │            │
│  ▼             ▼                ▼                  │            │
│  ┌───────┐  ┌──────┐  ┌──────────────┐             │            │
│  │GEMINI │  │CLAUDE│  │    GROQ      │             │            │
│  │VISION │  │      │  │ (Lightning)  │             │            │
│  └───┬───┘  └───┬──┘  └──────┬───────┘             │            │
│      │          │             │                    │            │
│      ▼          ▼             ▼                    │            │
│  Assembly   Pseudo-     Pattern Match              │            │
│  Visuals    Code        & Exploits                 │            │
│             Recon.      Detection                  │            │
│                                                                 │
│  Step 3: Results Aggregation                                    │
│  ┌─────────────────────────────────────────────────┐            │
│  │ - Combine all AI outputs                        │            │
│  │ - Generate unified report                       │            │
│  │ - Create actionable insights                    │            │
│  └─────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Technology Stack

### Frontend
- **Framework**: React or Vue.js
- **Styling**: TailwindCSS
- **Code Display**: Monaco Editor (syntax highlighting)
- **Diagrams**: Mermaid.js (control flow graphs)
- **File Upload**: react-dropzone / vue-dropzone

### Backend
- **API Server**: FastAPI (Python) or Express.js (Node.js)
- **Binary Analysis**:
  - **Radare2** - Disassembly framework
  - **Capstone** - Lightweight disassembler engine
- **AI Services**:
  - **Groq API** - Ultra-fast inference (pattern matching, exploit detection)
  - **Claude API (Anthropic)** - Code reconstruction & explanation
  - **Gemini API (Google)** - Visual assembly analysis & diagram generation
- **Database**: Supabase (PostgreSQL)
  - Real-time features for collaborative analysis
  - File storage for binary samples
  - User authentication

### Infrastructure
- **Deployment**: Vercel (frontend) + Railway/Fly.io (backend)
- **File Processing**: Sandboxed Docker containers for binary execution
- **Rate Limiting**: Redis (optional for API throttling)

---

## 📋 Data Flow

### Upload & Analysis Flow

```
1. USER UPLOADS BINARY
   │
   ├─► Frontend validates file (size, type)
   │
   └─► Send to Backend API
       │
       ├─► Store in Supabase Storage
       │
       ├─► Extract metadata (architecture, compiler, size)
       │
       └─► Queue for analysis
           │
           ▼
2. DISASSEMBLY PHASE (Radare2/Capstone)
   │
   ├─► Disassemble to assembly code
   ├─► Extract function boundaries
   ├─► Find hardcoded strings/constants
   └─► Generate control flow graph
       │
       ▼
3. PARALLEL AI ANALYSIS
   │
   ├─► GEMINI Vision API
   │   ├─ Input: Assembly + Control Flow Graph
   │   └─ Output: Visual diagram + Architecture insights
   │
   ├─► CLAUDE API
   │   ├─ Input: Assembly + Context
   │   └─ Output: Reconstructed pseudo-code + Explanations
   │
   └─► GROQ API (Fast)
       ├─ Input: Assembly patterns
       └─ Output: Vulnerabilities + Exploit suggestions + Performance
           │
           ▼
4. AGGREGATION & STORAGE
   │
   ├─► Combine all AI outputs
   ├─► Generate final report
   ├─► Store in Supabase
   └─► Return to frontend
       │
       ▼
5. DISPLAY RESULTS
   └─► Show side-by-side comparison
```

---

## 🤖 AI Models Integration

### 1. Gemini Vision (Google)
**Purpose**: Visual analysis of assembly and control flow

**Input**:
```python
# Example API call
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

response = model.generate_content([
    "Analyze this x86 assembly code and create a control flow diagram:",
    assembly_text,
    "Identify: functions, loops, conditionals, and data flow"
])
```

**Output**:
- Control flow graph (textual/Mermaid format)
- Architecture insights
- Function identification
- Data flow analysis

---

### 2. Claude (Anthropic)
**Purpose**: Source code reconstruction and explanation

**Input**:
```python
import anthropic

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": f"""Reconstruct the original source code from this assembly:

{assembly_code}

Provide:
1. Pseudo-code reconstruction
2. Explanation of what the code does
3. Identified vulnerabilities
4. Original programming language guess"""
    }]
)
```

**Output**:
- Reconstructed pseudo-code (Python/C-like)
- Line-by-line explanations
- Security analysis
- Code quality assessment

---

### 3. Groq (Fast Inference)
**Purpose**: Lightning-fast pattern matching and exploit detection

**Input**:
```python
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{
        "role": "user",
        "content": f"""Analyze this binary for:
1. Hardcoded passwords/keys
2. Buffer overflow vulnerabilities
3. Insecure functions (strcpy, gets, etc.)
4. Cryptographic weaknesses

Assembly:
{assembly_code}

Respond in JSON format with findings."""
    }],
    temperature=0.2,
    max_tokens=2048
)
```

**Output** (JSON):
```json
{
  "passwords": ["SECRET123", "admin"],
  "vulnerabilities": [
    {
      "type": "buffer_overflow",
      "location": "0x401234",
      "function": "scanf",
      "severity": "high"
    }
  ],
  "crypto_issues": ["XOR with static key 0x42"],
  "exploits": ["Stack overflow possible via input buffer"]
}
```

---

## 🗄️ Database Schema (Supabase)

### Table: `analyses`
```sql
CREATE TABLE analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  binary_name TEXT NOT NULL,
  binary_hash TEXT NOT NULL,
  file_size INTEGER,
  architecture TEXT, -- x86, x64, ARM, etc.
  compiler TEXT,     -- GCC, Clang, MSVC, etc.

  -- Analysis results (JSONB for flexibility)
  assembly_code TEXT,
  gemini_analysis JSONB,
  claude_reconstruction JSONB,
  groq_findings JSONB,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  processing_time_ms INTEGER,
  status TEXT DEFAULT 'pending' -- pending, processing, completed, failed
);

-- Index for faster lookups
CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX idx_analyses_binary_hash ON analyses(binary_hash);
```

### Table: `binary_files`
```sql
CREATE TABLE binary_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL, -- Supabase Storage path
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Supabase Storage Buckets
```javascript
// Create storage bucket for binaries
const { data, error } = await supabase
  .storage
  .createBucket('binary-samples', {
    public: false,
    fileSizeLimit: 52428800 // 50MB limit
  })
```

---

## 🔐 Security Considerations

### Binary Analysis Sandbox
```dockerfile
# Docker container for safe binary execution
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    radare2 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -s /bin/bash sandbox
USER sandbox

# Limit resources
WORKDIR /analysis
CMD ["python3", "analyze.py"]
```

**Safety Measures**:
- ✅ All binaries run in isolated Docker containers
- ✅ No network access during analysis
- ✅ Automatic timeout after 60 seconds
- ✅ File size limits (max 50MB)
- ✅ Malware scanning before processing
- ✅ Rate limiting per user

---

## 📊 API Endpoints

### Backend API (FastAPI)

```python
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"]
)

@app.post("/api/analyze")
async def analyze_binary(file: UploadFile = File(...)):
    """
    Upload and analyze a binary file
    Returns: analysis_id for tracking
    """
    pass

@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """
    Retrieve analysis results
    Returns: Full analysis report
    """
    pass

@app.get("/api/history")
async def get_user_history(user_id: str):
    """
    Get user's analysis history
    Returns: List of past analyses
    """
    pass

@app.post("/api/keygen/{analysis_id}")
async def generate_keygen(analysis_id: str):
    """
    Generate valid serial keys (if applicable)
    Returns: List of valid serials
    """
    pass
```

---

## 💻 Frontend Components

### Main UI Structure

```tsx
// React component structure
<App>
  <Header />
  <MainContent>
    <UploadZone />          // Drag & drop binary upload
    <AnalysisView>          // Main analysis display
      <TabView>
        <AssemblyTab />     // Raw assembly + Gemini visuals
        <PseudoCodeTab />   // Claude reconstruction
        <FindingsTab />     // Groq vulnerabilities
        <ControlFlowTab />  // Mermaid diagram
      </TabView>
    </AnalysisView>
    <HistorySidebar />      // Past analyses
  </MainContent>
</App>
```

### Analysis Display Example

```tsx
// Side-by-side comparison component
<div className="grid grid-cols-3 gap-4">
  {/* Assembly Column */}
  <div className="bg-gray-900 rounded-lg p-4">
    <h3>Assembly (Radare2)</h3>
    <MonacoEditor
      language="asm"
      value={assemblyCode}
      theme="vs-dark"
      readOnly
    />
  </div>

  {/* Pseudo-code Column */}
  <div className="bg-gray-900 rounded-lg p-4">
    <h3>Reconstructed Code (Claude)</h3>
    <MonacoEditor
      language="python"
      value={pseudoCode}
      theme="vs-dark"
      readOnly
    />
  </div>

  {/* AI Insights Column */}
  <div className="bg-gray-900 rounded-lg p-4">
    <h3>AI Analysis (Groq)</h3>
    <FindingsList findings={groqFindings} />
  </div>
</div>
```

---

## ⚡ Performance Optimizations

### Parallel AI Processing
```python
import asyncio
from typing import Dict, Any

async def analyze_with_all_ais(assembly: str) -> Dict[str, Any]:
    """Run all AI analyses in parallel"""

    tasks = [
        gemini_analyze(assembly),   # Visual analysis
        claude_reconstruct(assembly), # Code reconstruction
        groq_detect_vulns(assembly)  # Fast pattern matching
    ]

    results = await asyncio.gather(*tasks)

    return {
        "gemini": results[0],
        "claude": results[1],
        "groq": results[2]
    }
```

### Caching Strategy
```python
# Cache binary analyses by hash
import hashlib
from functools import lru_cache

def get_binary_hash(binary_data: bytes) -> str:
    return hashlib.sha256(binary_data).hexdigest()

@lru_cache(maxsize=100)
def get_cached_analysis(binary_hash: str):
    """Check if we've analyzed this binary before"""
    return supabase.table('analyses').select('*').eq('binary_hash', binary_hash).execute()
```

---

## 🚀 Deployment Strategy

### Frontend (Vercel)
```bash
# Build and deploy
npm run build
vercel --prod
```

### Backend (Railway/Fly.io)
```yaml
# railway.toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

### Environment Variables
```bash
# Backend .env
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
SUPABASE_URL=https://...
SUPABASE_KEY=...

# Frontend .env
VITE_API_URL=https://api.yourproject.com
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
```

---

## 🎯 Demo Flow (Hackathon Presentation)

### 5-Minute Demo Script

**1. Introduction (30s)**
> "We built an AI-powered reverse engineering tool that reconstructs source code from compiled binaries using 3 AI models in parallel."

**2. Upload Binary (30s)**
- Drag & drop `crackme.exe`
- Show real-time processing status

**3. Show Results (3 mins)**
- **Assembly view**: Raw disassembly from Radare2
- **Gemini analysis**: Control flow diagram
- **Claude reconstruction**: Python-like pseudo-code
- **Groq findings**: "PASSWORD FOUND: HACKATHON2024" (🎯 WOW moment!)
- Show vulnerability detection

**4. Generate Keygen (30s)**
- Click "Generate Valid Serials"
- Show 5 valid serial keys
- Verify one works

**5. Wrap-up (30s)**
> "Used Groq for speed, Claude for accuracy, Gemini for visuals, and Supabase for storage. All sponsor tracks covered!"

---

## 🎨 UI/UX Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 REVERSE ENGINEERING PLAYGROUND        [Upload] [Examples]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📤 Drop binary here or click to upload                         │
│  Supported: .exe, .elf, .dll, .so (max 50MB)                   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  📊 ANALYSIS RESULTS                                            │
│  ┌─────┬──────┬─────┬──────────┬─────────┐                     │
│  │asm  │code  │graph│findings  │history  │                     │
│  └─────┴──────┴─────┴──────────┴─────────┘                     │
│                                                                  │
│  ┌────────────────┬──────────────────┬──────────────────┐      │
│  │   ASSEMBLY     │  PSEUDO-CODE     │   AI INSIGHTS    │      │
│  │   (Radare2)    │   (Claude)       │   (Groq)         │      │
│  ├────────────────┼──────────────────┼──────────────────┤      │
│  │ [syntax        │ [python-like     │ 🎯 Findings:     │      │
│  │  highlighted   │  reconstruction] │                  │      │
│  │  assembly]     │                  │ ✅ Password:     │      │
│  │                │ def main():      │   "SECRET123"    │      │
│  │ mov eax, 0x1   │   password =     │                  │      │
│  │ ...            │   "secret123"    │ ⚠️ Vulnerabilities:│     │
│  │                │   if input ==    │ • Buffer overflow│      │
│  │                │     password:    │ • Weak crypto    │      │
│  └────────────────┴──────────────────┴──────────────────┘      │
│                                                                  │
│  🚀 QUICK ACTIONS:                                              │
│  [Generate Keygen] [Export Report] [Share Analysis]            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📝 Implementation Timeline (12 Hours Remaining)

### Hour 0-2: Setup & Infrastructure
- ✅ Initialize frontend (React + Vite + TailwindCSS)
- ✅ Setup backend (FastAPI)
- ✅ Configure Supabase project
- ✅ Setup AI API keys (Groq, Claude, Gemini)
- ✅ Create Docker sandbox environment

### Hour 2-5: Core Binary Analysis
- ✅ Integrate Radare2/Capstone for disassembly
- ✅ Build file upload & storage system
- ✅ Implement basic analysis pipeline
- ✅ Test with simple crackme binary

### Hour 5-8: AI Integration
- ✅ Integrate Groq API for pattern detection
- ✅ Integrate Claude API for code reconstruction
- ✅ Integrate Gemini API for visual analysis
- ✅ Implement parallel processing
- ✅ Store results in Supabase

### Hour 8-10: Frontend Polish
- ✅ Build analysis display UI
- ✅ Add Monaco Editor for code display
- ✅ Integrate Mermaid.js for diagrams
- ✅ Add history sidebar
- ✅ Responsive design

### Hour 10-12: Demo Prep & Testing
- ✅ Create demo binaries (crackme, keygen)
- ✅ End-to-end testing
- ✅ Deploy to production
- ✅ Prepare presentation slides
- ✅ Record backup demo video

---

## 🏆 Hackathon Sponsor Integration

### ✅ Groq
- Ultra-fast vulnerability detection
- Pattern matching in assembly code
- Exploit generation

### ✅ Anthropic (Claude)
- Source code reconstruction
- Detailed explanations
- Security analysis

### ✅ Google (Gemini)
- Visual assembly analysis
- Control flow graph generation
- Architecture insights

### ✅ Supabase
- Database for analysis history
- File storage for binaries
- Real-time collaboration features
- User authentication

---

## 🎓 Learning Resources

- [Radare2 Book](https://book.rada.re/)
- [Capstone Documentation](http://www.capstone-engine.org/documentation.html)
- [Groq API Cookbook](https://github.com/groq/groq-api-cookbook)
- [Claude API Reference](https://docs.anthropic.com/)
- [Gemini API Guide](https://ai.google.dev/gemini-api/docs)
- [Supabase Realtime](https://supabase.com/docs/guides/realtime)

---

## 📞 Technical Support & References

- **Radare2**: Headless mode for programmatic use
- **Capstone**: Lightweight disassembler (Python/C bindings)
- **Groq**: 200+ tokens/sec inference speed
- **Claude**: Best-in-class code understanding
- **Gemini**: Multimodal analysis capabilities
- **Supabase**: Real-time PostgreSQL

---

**Built for Cursor Singapore 24-Hour Hackathon 🇸🇬**
*Demonstrating the power of AI-assisted reverse engineering*
