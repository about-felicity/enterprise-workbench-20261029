import { install } from "undici";

// Use the maintained client so paused upstream sockets cannot crash the workbench.
install();
