import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { chatService } from "../services/chat";
import { papersService } from "../services/papers";
import { Conversation, Message, Paper, Citation } from "../types";
import Navbar from "../components/Navbar";
import { 
  MessageSquare, Plus, Trash2, Send, Sparkles, BookOpen, 
  ChevronRight, AlertCircle, FileText, Bookmark, Quote, Info 
} from "lucide-react";
import { API_BASE_URL } from "../services/api";

export default function ChatPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  // Chat State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  
  // Input State
  const [inputMessage, setInputMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);

  // UI State
  const [loadingChats, setLoadingChats] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // Initial loading
  const loadInitialData = async () => {
    setLoadingChats(true);
    try {
      // 1. Load active conversations
      const chatsList = await chatService.listConversations();
      setConversations(chatsList);
      
      // 2. Load papers list for multi-select filtering
      const papersList = await papersService.listPapers();
      setPapers(papersList);

      // 3. Resolve active chat session from sessionStorage if returning from another page
      let initialChatId = null;
      if (typeof window !== "undefined") {
        initialChatId = sessionStorage.getItem("rpa_active_chat_id");
        sessionStorage.removeItem("rpa_active_chat_id");
        
        // Check if user clicked "Chat" button from a specific paper
        const specPaperId = sessionStorage.getItem("rpa_selected_paper_id");
        if (specPaperId) {
          setSelectedPaperIds([specPaperId]);
          sessionStorage.removeItem("rpa_selected_paper_id");
        }
      }

      if (initialChatId) {
        handleSelectChat(initialChatId);
      } else if (chatsList.length > 0) {
        handleSelectChat(chatsList[0].id);
      } else {
        // Start a default new conversation if empty
        const defaultChat = await chatService.createConversation();
        setConversations([defaultChat]);
        handleSelectChat(defaultChat.id);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load conversation history.");
    } finally {
      setLoadingChats(false);
    }
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/login");
      return;
    }
    if (isAuthenticated) {
      loadInitialData();
    }
  }, [isAuthenticated, authLoading]);

  const handleSelectChat = async (chatId: string) => {
    setActiveChatId(chatId);
    setMessages([]);
    setStreamingContent("");
    setStreamingCitations([]);
    setSelectedCitation(null);
    setLoadingMessages(true);
    setError(null);

    try {
      const details = await chatService.getConversation(chatId);
      setMessages(details.messages || []);
    } catch (err) {
      setError("Could not load message history.");
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleCreateChat = async () => {
    setError(null);
    try {
      const newChat = await chatService.createConversation();
      setConversations((prev) => [newChat, ...prev]);
      handleSelectChat(newChat.id);
    } catch (err) {
      setError("Failed to create new conversation thread.");
    }
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation thread permanently?")) return;
    
    try {
      await chatService.deleteConversation(chatId);
      setConversations((prev) => prev.filter((c) => c.id !== chatId));
      
      if (activeChatId === chatId) {
        const remaining = conversations.filter((c) => c.id !== chatId);
        if (remaining.length > 0) {
          handleSelectChat(remaining[0].id);
        } else {
          setActiveChatId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      alert("Failed to delete conversation");
    }
  };

  const handlePaperCheckboxChange = (paperId: string) => {
    setSelectedPaperIds((prev) =>
      prev.includes(paperId)
        ? prev.filter((id) => id !== paperId)
        : [...prev, paperId]
    );
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isStreaming || !activeChatId) return;

    const userText = inputMessage;
    setInputMessage("");
    setError(null);
    setSelectedCitation(null);

    // Optimistically add user's message to UI list
    const tempUserMsg: Message = {
      id: Math.random().toString(),
      conversation_id: activeChatId,
      role: "user",
      content: userText,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    setIsStreaming(true);
    setStreamingContent("");
    setStreamingCitations([]);

    const accessToken = localStorage.getItem("rpa_access_token");
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat/conversations/${activeChatId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          content: userText,
          paper_ids: selectedPaperIds.length > 0 ? selectedPaperIds : null,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to initialize stream endpoint.");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) throw new Error("Body reader is unavailable.");

      let currentEvent = "";
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const rawText = decoder.decode(value);
        const lines = rawText.split("\n");
        
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event: ")) {
            currentEvent = trimmed.slice(7).trim();
          } else if (trimmed.startsWith("data: ")) {
            const dataContent = trimmed.slice(6).trim();
            
            if (currentEvent === "citations") {
              const citations = JSON.parse(dataContent);
              setStreamingCitations(citations);
            } else if (currentEvent === "token") {
              const token = JSON.parse(dataContent);
              setStreamingContent((prev) => prev + token);
            } else if (currentEvent === "done") {
              // Finish stream
            }
          }
        }
      }

      // After streaming finishes successfully, refresh conversation detail logs to get official IDs & timestamps
      const details = await chatService.getConversation(activeChatId);
      setMessages(details.messages || []);
      
      // Update sidebar conversation titles in case it got auto-named
      const chatsList = await chatService.listConversations();
      setConversations(chatsList);

    } catch (err: any) {
      console.error(err);
      setError("AI generation failed or connection was closed.");
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
      setStreamingCitations([]);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 overflow-hidden">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        {/* LEFT COLUMN: Chat sidebar and PDF multi-filters */}
        <aside className="w-80 border-r border-slate-800/80 bg-slate-950 flex flex-col justify-between hidden md:flex shrink-0">
          
          {/* Chat Sessions list */}
          <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Conversations</h3>
              <button
                onClick={handleCreateChat}
                className="flex items-center gap-1 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" /> New Chat
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {loadingChats ? (
                <div className="flex justify-center py-10">
                  <div className="h-5 w-5 animate-spin rounded-full border border-slate-800 border-t-indigo-500" />
                </div>
              ) : conversations.length === 0 ? (
                <p className="text-[10px] text-slate-500 italic py-6 text-center">No chats available.</p>
              ) : (
                conversations.map((chat) => {
                  const isActive = chat.id === activeChatId;
                  return (
                    <div
                      key={chat.id}
                      onClick={() => handleSelectChat(chat.id)}
                      className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer border transition-all text-xs ${
                        isActive
                           ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400 font-semibold"
                          : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 truncate max-w-[85%]">
                        <MessageSquare className="h-4 w-4 shrink-0 text-slate-500" />
                        <span className="truncate leading-none">{chat.title}</span>
                      </div>
                      <button
                        onClick={(e) => handleDeleteChat(chat.id, e)}
                        className="text-slate-600 hover:text-red-400 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-slate-800/50 transition-all shrink-0"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Document Multi-select filter widget */}
          <div className="border-t border-slate-800/80 p-4 space-y-3 bg-slate-900/10">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-indigo-400" /> Query Filters
              </h4>
              {selectedPaperIds.length > 0 && (
                <button
                  onClick={() => setSelectedPaperIds([])}
                  className="text-[9px] text-slate-500 hover:text-slate-300 font-semibold uppercase"
                >
                  Clear Selection
                </button>
              )}
            </div>
            <p className="text-[10px] text-slate-500 leading-normal">
              {selectedPaperIds.length === 0
                ? "Querying entire document library."
                : `Querying ${selectedPaperIds.length} selected papers.`}
            </p>

            <div className="max-h-[160px] overflow-y-auto space-y-2 pr-1">
              {papers.length === 0 ? (
                <p className="text-[9px] text-slate-600 italic py-2">No papers uploaded yet.</p>
              ) : (
                papers.map((paper) => {
                  const isChecked = selectedPaperIds.includes(paper.id);
                  return (
                    <label
                      key={paper.id}
                      className="flex items-start gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-300 select-none group"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handlePaperCheckboxChange(paper.id)}
                        disabled={paper.status !== "completed"}
                        className="mt-0.5 rounded border-slate-800 text-indigo-600 focus:ring-0 focus:ring-offset-0 disabled:opacity-30 cursor-pointer"
                      />
                      <span className={`text-[11px] truncate leading-tight ${isChecked ? "text-indigo-400 font-semibold" : ""}`} title={paper.title}>
                        {paper.title}
                      </span>
                    </label>
                  );
                })
              )}
            </div>
          </div>

        </aside>

        {/* MIDDLE CHAT WORKSPACE & RIGHT DRAWER */}
        <main className="flex-1 flex overflow-hidden">
          
          {/* Messages list & input area */}
          <div className="flex-1 flex flex-col justify-between overflow-hidden relative">
            
            {error && (
              <div className="absolute top-4 left-4 right-4 z-10 flex items-center gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-xs text-red-400">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <p className="font-medium">{error}</p>
              </div>
            )}

            {/* Chat Messages Log */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
              {loadingMessages ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-indigo-500" />
                  <p className="text-xs text-slate-400">Loading conversation log...</p>
                </div>
              ) : messages.length === 0 && !streamingContent ? (
                <div className="flex flex-col items-center justify-center h-full text-center p-6 gap-3">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shadow-md">
                    <Sparkles className="h-7 w-7" />
                  </div>
                  <h3 className="text-base font-bold text-white tracking-tight">AI Research Workspace</h3>
                  <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                    Ask questions about your uploaded documents. The AI helper will perform similarity retrieval and output answers backed by inline citations.
                  </p>
                </div>
              ) : (
                <div className="space-y-6 max-w-4xl mx-auto">
                  
                  {/* Messages Mapping */}
                  {messages.map((message) => {
                    const isUser = message.role === "user";
                    return (
                      <div
                        key={message.id}
                        className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}
                      >
                        {/* Avatar */}
                        {!isUser && (
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-blue-500 text-white font-bold text-xs shrink-0 select-none">
                            AI
                          </div>
                        )}
                        
                        <div className="space-y-2 max-w-[85%]">
                          {/* Message bubble */}
                          <div
                            className={`p-4 rounded-2xl text-xs leading-relaxed ${
                              isUser
                                ? "bg-indigo-600 text-white rounded-tr-none shadow-md"
                                : "glass-panel text-slate-200 rounded-tl-none"
                            }`}
                          >
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          </div>

                          {/* Citations Panel */}
                          {!isUser && message.citations && message.citations.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5 pl-1.5">
                              <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1 mr-1">
                                <Bookmark className="h-3 w-3" /> Citations:
                              </span>
                              {message.citations.map((cite, index) => (
                                <button
                                  key={index}
                                  onClick={() => setSelectedCitation(cite)}
                                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border text-[10px] font-semibold transition-all ${
                                    selectedCitation?.chunk_index === cite.chunk_index && selectedCitation?.paper_id === cite.paper_id
                                      ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-400 font-bold"
                                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                                  }`}
                                  title={`${cite.paper_title} (Page ${cite.page_number})`}
                                >
                                  <FileText className="h-3 w-3" />
                                  <span className="max-w-[120px] truncate">{cite.paper_title}</span>
                                  <span className="font-mono text-[9px] bg-slate-800 px-1 rounded">p.{cite.page_number}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {/* Streaming Block */}
                  {isStreaming && (streamingContent || streamingCitations.length > 0) && (
                    <div className="flex gap-4 justify-start animate-fade-in">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-blue-500 text-white font-bold text-xs shrink-0 select-none">
                        AI
                      </div>
                      <div className="space-y-2 max-w-[85%]">
                        {streamingContent && (
                          <div className="p-4 rounded-2xl text-xs leading-relaxed glass-panel text-slate-200 rounded-tl-none border-indigo-500/10 shadow-inner">
                            <p className="whitespace-pre-wrap inline">
                              {streamingContent}
                              <span className="inline-block h-3 w-1 bg-indigo-500 ml-1.5 animate-pulse align-middle" />
                            </p>
                          </div>
                        )}
                        
                        {streamingCitations.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 pl-1.5">
                            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1 mr-1">
                              <Bookmark className="h-3 w-3" /> Citations:
                            </span>
                            {streamingCitations.map((cite, index) => (
                              <button
                                key={index}
                                onClick={() => setSelectedCitation(cite)}
                                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 text-[10px] font-semibold transition-all ${
                                  selectedCitation?.chunk_index === cite.chunk_index && selectedCitation?.paper_id === cite.paper_id
                                    ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-400 font-bold"
                                    : "hover:text-slate-200 hover:bg-slate-850"
                                }`}
                              >
                                <FileText className="h-3 w-3" />
                                <span className="max-w-[120px] truncate">{cite.paper_title}</span>
                                <span className="font-mono text-[9px] bg-slate-800 px-1 rounded">p.{cite.page_number}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Empty spacer for anchor ref */}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input form */}
            <div className="border-t border-slate-800/80 p-4 bg-slate-950/60 backdrop-blur-md">
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-2">
                <input
                  type="text"
                  placeholder={
                    isStreaming
                      ? "Assistant is writing response..."
                      : activeChatId
                      ? "Ask a question about the papers..."
                      : "Create a conversation in the sidebar to begin..."
                  }
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  disabled={isStreaming || !activeChatId}
                  className="flex-1 px-4 py-3 rounded-xl glass-input text-xs disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isStreaming || !activeChatId}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-4.5 w-4.5" />
                </button>
              </form>
              
              {/* Query Filters Status for Mobile */}
              <div className="max-w-4xl mx-auto text-center mt-2.5 block md:hidden">
                <p className="text-[10px] text-slate-500">
                  {selectedPaperIds.length === 0
                    ? "Searching across all documents"
                    : `Searching across ${selectedPaperIds.length} selected documents`}
                </p>
              </div>
            </div>

          </div>

          {/* RIGHT DRAWER: Citation source details */}
          {selectedCitation && (
            <aside className="w-85 border-l border-slate-800/80 bg-slate-950 p-5 flex flex-col justify-between shrink-0 animate-fade-in relative z-20">
              {/* Internal Glowing Blob */}
              <div className="absolute top-1/4 right-1/4 h-[180px] w-[180px] rounded-full bg-indigo-500/5 blur-[80px] pointer-events-none" />
              
              <div className="space-y-5 flex-1 overflow-y-auto relative z-10">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-1.5">
                    <Quote className="h-4.5 w-4.5 text-indigo-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">Citation Context</h3>
                  </div>
                  <button
                    onClick={() => setSelectedCitation(null)}
                    className="text-slate-500 hover:text-slate-300 text-xs font-semibold"
                  >
                    Clear
                  </button>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="space-y-1">
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Document Title</h4>
                    <p className="text-slate-200 font-semibold leading-snug">{selectedCitation.paper_title}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[10px] font-mono">
                    <div className="p-2 bg-slate-900/60 border border-slate-800/60 rounded-xl">
                      <span className="text-slate-500 block text-[9px]">Page Number</span>
                      <span className="text-indigo-400 font-bold text-xs">p. {selectedCitation.page_number}</span>
                    </div>
                    <div className="p-2 bg-slate-900/60 border border-slate-800/60 rounded-xl">
                      <span className="text-slate-500 block text-[9px]">Segment ID</span>
                      <span className="text-indigo-400 font-bold text-xs">#{selectedCitation.chunk_index}</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Excerpt Text</h4>
                    <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-xl leading-relaxed italic text-slate-350 shadow-inner relative">
                      <div className="absolute top-2 left-2 text-slate-700 font-serif text-3xl leading-none">&ldquo;</div>
                      <p className="pl-3 pr-2 py-1">{selectedCitation.content}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-800/80 pt-4 mt-4 flex justify-end relative z-10">
                <button
                  onClick={() => setSelectedCitation(null)}
                  className="w-full py-2.5 border border-slate-800 hover:border-slate-750 bg-slate-950 hover:bg-slate-900 text-slate-400 hover:text-slate-200 text-[10px] font-bold uppercase rounded-xl transition-all"
                >
                  Close Citation
                </button>
              </div>

            </aside>
          )}

        </main>
      </div>
    </div>
  );
}
