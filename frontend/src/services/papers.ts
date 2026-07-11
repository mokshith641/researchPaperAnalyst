import api, { API_BASE_URL } from "./api";
import { Paper, SearchResult, SummaryResponse } from "../types";

export const papersService = {
  listPapers: async (search?: string, limit = 50): Promise<Paper[]> => {
    const response = await api.get("/papers", {
      params: { search, limit },
    });
    return response.data;
  },

  getPaper: async (paperId: string): Promise<Paper> => {
    const response = await api.get(`/papers/${paperId}`);
    return response.data;
  },

  getStats: async (): Promise<{ total_papers: number }> => {
    const response = await api.get("/papers/stats");
    return response.data;
  },

  uploadPapers: async (
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<Paper[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await api.post("/papers/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
    return response.data;
  },

  deletePaper: async (paperId: string): Promise<void> => {
    await api.delete(`/papers/${paperId}`);
  },

  renamePaper: async (paperId: string, title: string): Promise<Paper> => {
    const response = await api.put(`/papers/${paperId}`, { title });
    return response.data;
  },

  downloadPaperUrl: (paperId: string): string => {
    return `${API_BASE_URL}/api/papers/${paperId}/download`;
  },

  downloadPaperFile: async (paperId: string, fileName: string): Promise<void> => {
    const response = await api.get(`/papers/${paperId}/download`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },

  semanticSearch: async (query: string, paperIds?: string[], limit = 5): Promise<SearchResult[]> => {
    const response = await api.post("/papers/search/semantic", {
      query,
      paper_ids: paperIds,
      limit,
    });
    return response.data;
  },

  summarizePaper: async (paperId: string): Promise<SummaryResponse> => {
    const response = await api.get(`/papers/${paperId}/summarize`);
    return response.data;
  },
};
