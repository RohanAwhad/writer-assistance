import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

const rootEl = document.getElementById("root");
if (rootEl === null) throw new Error("missing #root element");
createRoot(rootEl).render(<App />);
