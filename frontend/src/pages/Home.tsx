import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Link } from "react-router-dom";
import { 
  Sparkles, FileText, Search, BookOpen, MessageSquare, 
  ArrowRight, ShieldCheck, Cpu, Database, ChevronRight 
} from "lucide-react";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  // If already logged in, redirect them to dashboard directly
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-800 border-t-indigo-500" />
          <p className="text-sm font-medium text-slate-400 animate-pulse-subtle">
            Initializing AI workspace...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden relative">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-0 left-1/4 h-[500px] w-[500px] rounded-full bg-indigo-500/10 blur-[150px] pointer-events-none animate-pulse-glow" />
      <div className="absolute top-1/3 right-1/4 h-[600px] w-[600px] rounded-full bg-blue-500/10 blur-[180px] pointer-events-none animate-pulse-glow" />
      
      {/* Background SVG Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-35 pointer-events-none" />

      {/* Navigation Header */}
      <header className="sticky top-0 z-40 w-full border-b border-slate-900/60 bg-slate-950/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-blue-500 text-white font-bold text-base shadow-md shadow-indigo-500/20">
              RP
            </div>
            <span className="text-base font-bold text-white tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Research Assistant
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link 
              to="/login" 
              className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
            >
              Sign In
            </Link>
            <Link 
              to="/register" 
              className="flex items-center gap-1 px-4 py-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-indigo-500/10 active:scale-98"
            >
              Register <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pt-20 pb-16 text-center space-y-6 relative z-10 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-[10px] font-bold text-indigo-400 uppercase tracking-widest animate-pulse-subtle">
          <Sparkles className="h-3.5 w-3.5" /> Next-Gen AI Research Workspace
        </div>
        
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-none bg-gradient-to-b from-white via-slate-100 to-slate-500 bg-clip-text text-transparent py-2">
          Research Paper Analyst
        </h1>
        
        <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Upload complex academic PDFs, index them semantically using offline embeddings, and get instant summaries, key takeaways, and question-answering backed by precise inline source citations.
        </p>

        <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-6">
          <Link 
            to="/register" 
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-semibold text-xs uppercase tracking-wider rounded-xl transition-all shadow-lg shadow-indigo-500/25 active:scale-98"
          >
            Get Started For Free <ArrowRight className="h-4 w-4" />
          </Link>
          <Link 
            to="/login" 
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 text-slate-300 font-semibold text-xs uppercase tracking-wider rounded-xl transition-all shadow-inner active:scale-98"
          >
            Access Dashboard
          </Link>
        </div>
      </section>

      {/* Feature Grid Section */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 border-t border-slate-900/60 relative z-10">
        <div className="text-center mb-16 space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">Full-Stack Features Included</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Everything you need to digest, query, and search dense publications in seconds.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shadow-md">
              <FileText className="h-5.5 w-5.5" />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">PDF Chunking</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts text layouts, handles page boundaries, and segments articles into optimized overlapping vector blocks.
            </p>
          </div>

          {/* Card 2 */}
          <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 shadow-md">
              <Search className="h-5.5 w-5.5" />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">Semantic Vector Search</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Indices papers offline using local fast embeddings models to perform concept queries without calling paid APIs.
            </p>
          </div>

          {/* Card 3 */}
          <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shadow-md">
              <BookOpen className="h-5.5 w-5.5" />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">AI Summaries & ELI5</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generate instant abstracts, simplified explanation translations, and key takeaways for any indexed document.
            </p>
          </div>

          {/* Card 4 */}
          <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 shadow-md">
              <MessageSquare className="h-5.5 w-5.5" />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">Cited RAG Chats</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Chat with papers using session memories. Responses display clickable source citations to read the exact excerpt.
            </p>
          </div>
        </div>
      </section>

      {/* Tech Stack Banner */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 border-t border-slate-900/60 bg-slate-950/20 relative z-10 text-center space-y-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          <Cpu className="h-3.5 w-3.5" /> Architecture Stack
        </div>
        <h3 className="text-lg font-bold tracking-tight">Built on Modern Engineering Foundations</h3>
        
        <div className="flex flex-wrap justify-center items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/50 border border-slate-800/80 rounded-lg">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" /> React + Vite
          </div>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/50 border border-slate-800/80 rounded-lg">
            <Cpu className="h-3.5 w-3.5 text-blue-400" /> FastAPI
          </div>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/50 border border-slate-800/80 rounded-lg">
            <Database className="h-3.5 w-3.5 text-amber-400" /> Qdrant Cloud
          </div>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/50 border border-slate-800/80 rounded-lg">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> FastEmbed
          </div>
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/50 border border-slate-800/80 rounded-lg">
            <Sparkles className="h-3.5 w-3.5 text-purple-400" /> Groq Llama 3.3
          </div>
        </div>
      </section>

      {/* Call to Action Footer Section */}
      <section className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-20 text-center relative z-10 space-y-6">
        <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
          Ready to supercharge your research workflow?
        </h2>
        <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
          Create a free account, upload your reference publications, and start querying instantly.
        </p>
        <div>
          <Link 
            to="/register" 
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-semibold text-xs uppercase tracking-wider rounded-xl transition-all shadow-md shadow-indigo-500/15 active:scale-98 animate-pulse-subtle"
          >
            Create Free Account <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-900/60 py-8 text-center text-[10px] text-slate-500 bg-slate-950 z-10 relative">
        <p>© {new Date().getFullYear()} Research Paper Assistant. Capstone Project. All rights reserved.</p>
      </footer>
    </div>
  );
}
