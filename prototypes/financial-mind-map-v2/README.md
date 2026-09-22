# Financial Mind Map visual rewrite (prototype)

This is the React/Vite visual rewrite supplied in the MimoClaw workspace. Run it with `npm ci` and `npm run dev`; `npm run build` produces a static site.

It is a **separate prototype**, not a replacement for the FastAPI application in `frontend/`. Its financial records are sample data and browser `localStorage`; its displayed unlock control is not account authentication. Bank linking and sync are simulated. Do not enter real financial records or credentials into this prototype. The original workspace's Supabase functions and unused scaffolding were intentionally omitted because they have not been integrated with the Python API or reviewed for deployment.

To make this the production UI, replace the browser state with authenticated calls to the existing Python API, map the data models, and verify persistence and authorization before switching the served frontend.
