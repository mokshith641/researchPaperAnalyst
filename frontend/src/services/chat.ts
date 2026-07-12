import api from "./api";
import { Conversation, ConversationDetail } from "../types";

export const chatService = {
  listConversations: async (skip = 0, limit = 50): Promise<Conversation[]> => {
    const response = await api.get("/chat/conversations", {
      params: { skip, limit },
    });
    return response.data;
  },

  getConversation: async (conversationId: string): Promise<ConversationDetail> => {
    const response = await api.get(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  createConversation: async (): Promise<Conversation> => {
    const response = await api.post("/chat/conversations");
    return response.data;
  },

  renameConversation: async (conversationId: string, title: string): Promise<Conversation> => {
    const response = await api.put(`/chat/conversations/${conversationId}`, { title });
    return response.data;
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    await api.delete(`/chat/conversations/${conversationId}`);
  },
};
