import React from "react";
import { BrowserRouter } from "react-router-dom";
import Providers from "./components/Providers";
import AppRoutes from "./routes/AppRoutes";

export default function App() {
  return (
    <BrowserRouter>
      <Providers>
        <AppRoutes />
      </Providers>
    </BrowserRouter>
  );
}
