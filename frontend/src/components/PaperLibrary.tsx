"use client";

import React, { useState } from "react";
import { createPortal } from "react-dom";
import { Paper } from "../types";
import { papersService } from "../services/papers";
import { 
  FileText, Download, Trash2, MessageSquare, Sparkles, 
  Search, RefreshCw, AlertCircle, FileDigit, HelpCircle, FileCheck, X, Pencil
} from "lucide-react";
import { useNavigate } from "react-router-dom";

interface PaperLibraryProps {
  papers: Paper[];
  isLoading: boolean;
  onRefresh: () => void;
}

export default function PaperLibrary({ papers, isLoading, onRefresh }: PaperLibraryProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  // Summary modal state
  const [selectedPaperSummary, setSelectedPaperSummary] = useState<Paper | null>(null);
  const [summaryData, setSummaryData] = useState<any | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Paper rename state
  const [editingPaperId, setEditingPaperId] = useState<string | null>(null);
  const [editingPaperTitle, setEditingPaperTitle] = useState("");

  const handleRenamePaper = async (paperId: string, newTitle: string) => {
    if (!newTitle.trim()) {
      setEditingPaperId(null);
      return;
    }
    try {
      await papersService.renamePaper(paperId, newTitle.trim());
      onRefresh();
    } catch (err) {
      alert("Failed to rename paper");
    } finally {
      setEditingPaperId(null);
    }
  };

  // Filter papers
  const filteredPapers = papers.filter((paper) =>
    paper.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async (paperId: string) => {
    if (!confirm("Are you sure you want to delete this paper? This will also remove all its indexed vector chunks.")) return;
    setDeletingId(paperId);
    try {
      await papersService.deletePaper(paperId);
      onRefresh();
    } catch (err) {
      alert("Failed to delete paper");
    } finally {
      setDeletingId(null);
    }
  };

  const handleSummarize = async (paper: Paper) => {
    setSelectedPaperSummary(paper);
    setIsLoadingSummary(true);
    setSummaryError(null);
    setSummaryData(null);
    
    try {
      const summary = await papersService.summarizePaper(paper.id);
      setSummaryData(summary);
    } catch (err: any) {
      setSummaryError(err.response?.data?.detail || "Failed to load summary.");
    } finally {
      setIsLoadingSummary(false);
    }
  };

  const startChatWithPaper = (paperId: string) => {
    // Navigate to chat space, passing selected paper ID in sessionStorage or searchParams
    if (typeof window !== "undefined") {
      sessionStorage.setItem("rpa_selected_paper_id", paperId);
    }
    navigate("/chat");
  };

  const getStatusBadge = (status: string, error?: string | null) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
            <FileCheck className="h-3 w-3" /> Completed
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20 animate-pulse-subtle">
            <RefreshCw className="h-3 w-3 animate-spin" /> Processing
          </span>
        );
      case "failed":
        return (
          <span
            title={error || "Unknown processing error"}
            className="inline-flex items-center gap-1 rounded-md bg-red-500/10 px-2 py-1 text-xs font-semibold text-red-400 border border-red-500/20 cursor-help"
          >
            <AlertCircle className="h-3 w-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-400 border border-blue-500/20">
            <RefreshCw className="h-3 w-3" /> Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters & Actions Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search papers by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs rounded-xl glass-input"
          />
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3 py-2 border border-slate-800 hover:border-slate-700 bg-slate-950 hover:bg-slate-900 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 transition-all active:scale-98"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh List
        </button>
      </div>

      {/* Library Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
            <p className="text-xs text-slate-400 animate-pulse-subtle">Loading paper library...</p>
          </div>
        ) : filteredPapers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <FileText className="h-10 w-10 text-slate-600 mb-2" />
            <h4 className="text-sm font-semibold text-slate-300">No research papers found</h4>
            <p className="text-xs text-slate-500 max-w-xs mt-1">
              {search ? "No results match your search query." : "Upload a PDF paper above to begin chunking and analyzing."}
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/30 text-xs font-bold text-slate-400">
                <th className="p-4">Title</th>
                <th className="p-4 hidden md:table-cell">Pages</th>
                <th className="p-4 hidden sm:table-cell">Size</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {filteredPapers.map((paper) => (
                <tr key={paper.id} className="hover:bg-slate-900/30 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3 max-w-[280px] sm:max-w-[400px]">
                      <FileText className="h-5 w-5 text-indigo-400 shrink-0" />
                      <div className="truncate flex-1">
                        {editingPaperId === paper.id ? (
                          <input
                            type="text"
                            value={editingPaperTitle}
                            onChange={(e) => setEditingPaperTitle(e.target.value)}
                            onKeyDown={async (e) => {
                              if (e.key === "Enter") {
                                await handleRenamePaper(paper.id, editingPaperTitle);
                              }
                              if (e.key === "Escape") {
                                setEditingPaperId(null);
                              }
                            }}
                            onBlur={async () => {
                              await handleRenamePaper(paper.id, editingPaperTitle);
                            }}
                            autoFocus
                            className="bg-slate-900 text-white text-xs px-2 py-0.5 rounded border border-indigo-500 focus:outline-none w-full max-w-[300px]"
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <div 
                            className="font-semibold text-slate-200 truncate cursor-pointer hover:text-indigo-400 flex items-center gap-1.5 group/title"
                            onClick={() => {
                              setEditingPaperId(paper.id);
                              setEditingPaperTitle(paper.title);
                            }}
                            title="Click to rename paper"
                          >
                            <span className="truncate">{paper.title}</span>
                            <Pencil className="h-3 w-3 text-slate-500 opacity-0 group-hover/title:opacity-100 transition-opacity shrink-0" />
                          </div>
                        )}
                        <p className="text-[10px] text-slate-500 truncate" title={paper.file_name}>
                          {paper.file_name}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 hidden md:table-cell text-slate-300 font-mono">
                    {paper.num_pages || "--"}
                  </td>
                  <td className="p-4 hidden sm:table-cell text-slate-400 font-mono">
                    {(paper.file_size / (1024 * 1024)).toFixed(2)} MB
                  </td>
                  <td className="p-4">{getStatusBadge(paper.status, paper.error_message)}</td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {paper.status === "completed" && (
                        <>
                          <button
                            onClick={() => handleSummarize(paper)}
                            title="AI Summarizer"
                            className="p-2 border border-slate-800 hover:border-slate-700 bg-slate-950 hover:bg-slate-900 text-indigo-400 hover:text-indigo-300 rounded-lg transition-colors"
                          >
                            <Sparkles className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => startChatWithPaper(paper.id)}
                            title="Chat with Paper"
                            className="p-2 border border-indigo-900/30 hover:border-indigo-800 bg-indigo-950/20 hover:bg-indigo-950/50 text-indigo-400 hover:text-indigo-300 rounded-lg transition-colors"
                          >
                            <MessageSquare className="h-4 w-4" />
                          </button>
                        </>
                      )}
                      
                      <button
                        onClick={() => papersService.downloadPaperFile(paper.id, paper.file_name)}
                        title="Download PDF"
                        className="p-2 border border-slate-800 hover:border-slate-700 bg-slate-950 hover:bg-slate-900 text-slate-400 hover:text-slate-200 rounded-lg transition-colors"
                      >
                        <Download className="h-4 w-4" />
                      </button>

                      <button
                        onClick={() => handleDelete(paper.id)}
                        disabled={deletingId === paper.id}
                        title="Delete Paper"
                        className="p-2 border border-slate-800 hover:border-red-950 hover:bg-red-950/10 text-slate-500 hover:text-red-400 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Summarizer Sidebar/Dialog */}
      {selectedPaperSummary && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-950/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-2xl h-full rounded-2xl glass-panel shadow-2xl p-6 flex flex-col justify-between overflow-hidden relative">
            {/* Background glowing effects for premium style */}
            <div className="absolute top-10 right-10 h-[200px] w-[200px] rounded-full bg-indigo-500/10 blur-[80px] pointer-events-none" />
            <div className="absolute bottom-10 left-10 h-[200px] w-[200px] rounded-full bg-emerald-500/5 blur-[80px] pointer-events-none" />
            
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-4 relative z-10">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400 shrink-0" />
                <h3 className="text-base font-bold text-white tracking-tight truncate max-w-[450px]" title={selectedPaperSummary.title}>
                  AI Analysis: {selectedPaperSummary.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedPaperSummary(null)}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
 
            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto space-y-6 pr-2 relative z-10">
              {isLoadingSummary ? (
                <div className="flex flex-col items-center justify-center h-64 gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
                  <p className="text-xs text-slate-400 animate-pulse-subtle">Generating AI summaries and simplified breakdowns...</p>
                </div>
              ) : summaryError ? (
                <div className="flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-xs text-red-400">
                  <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Error Loading Summary</p>
                    <p className="text-slate-300 mt-1">{summaryError}</p>
                  </div>
                </div>
              ) : summaryData ? (
                <div className="space-y-6 text-xs text-slate-300 leading-relaxed">
                  
                  {/* Abstract Section */}
                  <div className="space-y-1.5">
                    <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Document Abstract</h4>
                    <p className="p-3.5 bg-indigo-950/10 border border-indigo-900/20 rounded-xl italic">
                      &ldquo;{summaryData.abstract}&rdquo;
                    </p>
                  </div>
 
                  {/* Summary Section */}
                  <div className="space-y-1.5">
                    <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Key Findings & Contributions</h4>
                    <p className="p-3.5 bg-slate-900/40 border border-slate-800/80 rounded-xl leading-relaxed">
                      {summaryData.summary}
                    </p>
                  </div>

                  {/* Keyword Explanation Section */}
                  {summaryData.explain_keywords && (
                    <div className="space-y-1.5">
                      <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Keyword-Focused Explanation</h4>
                      <p className="p-3.5 bg-indigo-950/10 border border-indigo-900/20 rounded-xl leading-relaxed">
                        {summaryData.explain_keywords}
                      </p>
                    </div>
                  )}

                  {/* Major Keywords Section */}
                  {summaryData.keywords && summaryData.keywords.length > 0 && (
                    <div className="space-y-1.5">
                      <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Major Keywords</h4>
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        {summaryData.keywords.map((kw: string, idx: number) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 text-[10px] font-semibold bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 rounded-lg select-none transition-all duration-200"
                          >
                            #{kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
 
                  {/* ELI5 / Explanation Section */}
                  <div className="space-y-1.5">
                    <h4 className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1.5">
                      <HelpCircle className="h-4 w-4" /> Explain like I&apos;m 5 (ELI5)
                    </h4>
                    <p className="p-3.5 bg-emerald-950/5 border border-emerald-900/20 rounded-xl text-slate-200 font-medium">
                      {summaryData.explain_simple}
                    </p>
                  </div>
 
                  {/* Key points Section */}
                  {summaryData.key_points && summaryData.key_points.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Key Takeaways</h4>
                      <ul className="space-y-2 pl-1">
                        {summaryData.key_points.map((point: string, i: number) => (
                          <li key={i} className="flex items-start gap-2.5">
                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
 
                </div>
              ) : null}
            </div>
 
            {/* Modal Footer */}
            <div className="pt-4 border-t border-slate-800/80 mt-4 flex justify-end relative z-10">
              <button
                onClick={() => setSelectedPaperSummary(null)}
                className="px-4 py-2 border border-slate-800 hover:border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200 text-xs font-semibold rounded-xl transition-all"
              >
                Close Summary
              </button>
            </div>
          </div>
        </div>,
        document.body
      )
    }
    </div>
  );
}
