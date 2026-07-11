"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { papersService } from "../../services/papers";
import { chatService } from "../../services/chat";
import { Paper, SearchResult, Conversation } from "../../types";
import Navbar from "../../components/Navbar";
import UploadDialog from "../../components/UploadDialog";
import PaperLibrary from "../../components/PaperLibrary";
import { 
  Upload, FileText, MessageSquare, Search, Sparkles, 
  HelpCircle, ChevronRight, AlertCircle, BookOpen 
} from "lucide-react";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Dialog State
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Data States
  const [papers, setPapers] = useState<Paper[]>([]);
  const [totalPapers, setTotalPapers] = useState(0);
  const [recentChats, setRecentChats] = useState<Conversation[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Semantic Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoadingData(true);
    try {
      const papersList = await papersService.listPapers();
      setPapers(papersList);
      
      const stats = await papersService.getStats();
      setTotalPapers(stats.total_papers);
      
      const chatsList = await chatService.listConversations(0, 5);
      setRecentChats(chatsList);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
      return;
    }
    if (isAuthenticated) {
      fetchDashboardData();
    }
  }, [isAuthenticated, authLoading, router]);

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const results = await papersService.semanticSearch(searchQuery);
      setSearchResults(results);
    } catch (err: any) {
      setSearchError(err.response?.data?.detail || "Semantic search failed. Try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const startNewChat = async () => {
    try {
      const newChat = await chatService.createConversation();
      router.push("/chat");
    } catch (err) {
      alert("Failed to start new chat");
    }
  };

  const openExistingChat = (chatId: string) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("rpa_active_chat_id", chatId);
    }
    router.push("/chat");
  };

  if (authLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 pb-12">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        
        {/* Dashboard Welcome Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Dashboard Overview</h2>
            <p className="text-xs text-slate-400">Welcome, {user?.full_name || user?.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={startNewChat}
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-all shadow-inner active:scale-98"
            >
              <MessageSquare className="h-4 w-4 text-indigo-400" />
              New Conversation
            </button>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-semibold rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-98"
            >
              <Upload className="h-4 w-4" />
              Upload PDF
            </button>
          </div>
        </div>

        {/* Metric Summaries */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Total Papers</p>
              <p className="text-2xl font-extrabold text-white mt-0.5">{totalPapers}</p>
            </div>
          </div>
          <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Completed Indexing</p>
              <p className="text-2xl font-extrabold text-white mt-0.5">
                {papers.filter((p) => p.status === "completed").length}
              </p>
            </div>
          </div>
          <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <MessageSquare className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Recent Chats</p>
              <p className="text-2xl font-extrabold text-white mt-0.5">{recentChats.length}</p>
            </div>
          </div>
        </div>

        {/* Middle Layout: Semantic Search vs Recent Chats */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Vector Semantic Search */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-400" />
              <h3 className="text-sm font-bold text-white tracking-tight">Semantic Vector Search</h3>
            </div>
            <p className="text-xs text-slate-400">
              Query concepts or topics across all your research documents directly using AI semantic similarity math.
            </p>

            <form onSubmit={handleSemanticSearch} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask e.g. 'What are the main performance limits of transformer models?'"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-xl glass-input text-xs"
              />
              <button
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
                className="flex items-center justify-center px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors disabled:opacity-50"
              >
                {isSearching ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
              </button>
            </form>

            {searchError && (
              <div className="flex items-center gap-3 rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-xs text-red-400">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <p>{searchError}</p>
              </div>
            )}

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  Semantic Matches ({searchResults.length})
                </h4>
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                  {searchResults.map((result, i) => (
                    <div
                      key={i}
                      className="p-3.5 bg-slate-900/40 border border-slate-800/80 hover:border-slate-800 rounded-xl space-y-2 text-xs"
                    >
                      <div className="flex justify-between items-center text-[10px] font-semibold text-slate-400">
                        <span className="text-indigo-400 font-bold truncate max-w-[200px]" title={result.paper_title}>
                          {result.paper_title}
                        </span>
                        <div className="flex items-center gap-2 font-mono">
                          <span>Page {result.page_number}</span>
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />
                          <span className="text-emerald-400">Match: {(result.score * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <p className="text-slate-300 leading-relaxed italic">&ldquo;{result.content}&rdquo;</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recent Conversations */}
          <div className="glass-panel p-6 rounded-2xl space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-white tracking-tight">Recent Conversations</h3>
              </div>

              {loadingData ? (
                <div className="flex justify-center py-10">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
                </div>
              ) : recentChats.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No active chats. Start one to query your library!
                </div>
              ) : (
                <div className="space-y-2">
                  {recentChats.map((chat) => (
                    <button
                      key={chat.id}
                      onClick={() => openExistingChat(chat.id)}
                      className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-900/20 hover:bg-slate-900/60 border border-slate-800/40 hover:border-slate-800 transition-all text-xs text-left group"
                    >
                      <div className="truncate pr-4">
                        <p className="font-semibold text-slate-300 truncate group-hover:text-slate-200">
                          {chat.title}
                        </p>
                        <p className="text-[9px] text-slate-500 mt-0.5">
                          {new Date(chat.updated_at).toLocaleDateString()}
                        </p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={startNewChat}
              className="w-full mt-4 py-2.5 rounded-xl border border-dashed border-slate-800 hover:border-slate-700 bg-slate-950 hover:bg-slate-900 text-slate-400 hover:text-slate-200 text-xs font-semibold transition-all active:scale-98"
            >
              + Create New Chat Thread
            </button>
          </div>
        </div>

        {/* Paper Library Table */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-indigo-400" />
              <h3 className="text-sm font-bold text-white tracking-tight">Research Paper Library</h3>
            </div>
            <span className="text-[10px] bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded-full font-bold">
              {papers.length} Papers
            </span>
          </div>

          <PaperLibrary
            papers={papers}
            isLoading={loadingData}
            onRefresh={fetchDashboardData}
          />
        </div>

      </main>

      {/* Upload Dialog Modal */}
      <UploadDialog
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={fetchDashboardData}
      />
    </div>
  );
}
