import React from "react";
import { createRoot } from "react-dom/client";
import { Options } from "./Options";
import "../../assets/globals.css";

const el = document.getElementById("root");
if (!el) throw new Error("missing #root");
createRoot(el).render(
  <React.StrictMode>
    <Options />
  </React.StrictMode>,
);
