"use client";

import React, { useState, useRef } from "react";
import { papersService } from "../services/papers";
import { X, UploadCloud, AlertCircle, FileText, CheckCircle2 } from "lucide-react";

interface UploadDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

export default function UploadDialog({ isOpen, onClose, onUploadSuccess }: UploadDialogProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateFiles = (files: File[]): File[] => {
    setError(null);
    const validFiles: File[] = [];
    const maxBytes = 25 * 1024 * 1024; // 25MB

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError(`"${file.name}" is not a PDF file. Only PDF files are supported.`);
        return [];
      }
      if (file.size > maxBytes) {
        setError(`"${file.name}" exceeds the maximum 25MB file size limit.`);
        return [];
      }
      validFiles.push(file);
    }
    return validFiles;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const validated = validateFiles(droppedFiles);
      if (validated.length > 0) {
        setSelectedFiles((prev) => [...prev, ...validated]);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const files = Array.from(e.target.files);
      const validated = validateFiles(files);
      if (validated.length > 0) {
        setSelectedFiles((prev) => [...prev, ...validated]);
      }
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    if (selectedFiles.length <= 1) {
      setError(null);
    }
  };

  const startUpload = async () => {
    if (selectedFiles.length === 0) return;
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);
    
    try {
      await papersService.uploadPapers(selectedFiles, (progress) => {
        setUploadProgress(progress);
      });
      setSuccess(true);
      setTimeout(() => {
        onUploadSuccess();
        handleClose();
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to upload files. Please try again.");
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    setSelectedFiles([]);
    setError(null);
    setSuccess(false);
    setIsUploading(false);
    setUploadProgress(0);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl glass-panel shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-6">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">Upload Research Papers</h3>
            <p className="text-xs text-slate-400">PDFs are processed and vectorized automatically</p>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        {success ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 animate-bounce">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <h4 className="text-base font-bold text-white">Upload Successful!</h4>
            <p className="text-xs text-slate-400">Starting text extraction and embedding in the background...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {error && (
              <div className="flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-xs text-red-400">
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <p className="font-medium leading-relaxed">{error}</p>
              </div>
            )}

            {/* Drag & Drop Area */}
            {!isUploading && (
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl py-8 px-4 cursor-pointer transition-all ${
                  dragActive
                    ? "border-indigo-500 bg-indigo-500/5 shadow-inner shadow-indigo-500/5"
                    : "border-slate-800 hover:border-slate-700 bg-slate-900/20 hover:bg-slate-900/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <UploadCloud className={`h-10 w-10 mb-3 transition-colors ${dragActive ? "text-indigo-400" : "text-slate-500"}`} />
                <p className="text-sm font-semibold text-slate-200">Drag & drop your files here</p>
                <p className="text-xs text-slate-400 mt-1">or click to browse from folder</p>
                <p className="text-[10px] text-slate-500 mt-4 font-mono">Maximum size: 25MB per PDF</p>
              </div>
            )}

            {/* Selected Files List */}
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Files to Upload ({selectedFiles.length})
                </h4>
                <div className="max-h-[140px] overflow-y-auto space-y-1.5 pr-1">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-lg bg-slate-900/60 border border-slate-800/80 px-3 py-2 text-xs"
                    >
                      <div className="flex items-center gap-2.5 truncate max-w-[80%]">
                        <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                        <span className="truncate text-slate-200 font-medium">{file.name}</span>
                        <span className="text-[10px] text-slate-500 shrink-0">
                          ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                        </span>
                      </div>
                      {!isUploading && (
                        <button
                          onClick={() => removeFile(index)}
                          className="text-slate-500 hover:text-red-400 p-1 hover:bg-slate-800 rounded transition-colors"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Uploading Progress */}
            {isUploading && (
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-indigo-400 animate-pulse-subtle">Uploading files...</span>
                  <span className="text-slate-400">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="bg-gradient-to-r from-indigo-500 to-blue-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Actions */}
            {!success && (
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800/80">
                <button
                  onClick={handleClose}
                  disabled={isUploading}
                  className="px-4 py-2 border border-slate-800 hover:border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200 text-xs font-semibold rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={startUpload}
                  disabled={selectedFiles.length === 0 || isUploading}
                  className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:from-indigo-950 disabled:to-blue-950 text-white disabled:text-slate-500 text-xs font-semibold rounded-xl transition-all shadow-md shadow-indigo-500/10 active:scale-98"
                >
                  Start Processing
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
