# ContextDesk Lab — frontend

Next.js app for the context engineering playground. It renders every answer
beside its execution record: the path through cache, memory, retrieval, and the
model; what reached the model and what was left out; and what each step cost.

```bash
npm install
npm run dev              # run on :3000 — needs the backend on :8000
npm run lint
npx tsc --noEmit
npm run build
```

The backend address defaults to `http://localhost:8000`. Set
`NEXT_PUBLIC_API_URL` in `frontend/.env.local` to point elsewhere.

This is Next.js 16 with the React Compiler and Tailwind CSS v4. Its docs ship in
`node_modules/next/dist/docs/`; check there before relying on older Next.js
habits.

- `../docs/FRONTEND_GUIDE.md` — a guided reading of the frontend code
- `../docs/ARCHITECTURE.md` — how the system is put together and why
- `../CLAUDE.md` — conventions for working in this repo
