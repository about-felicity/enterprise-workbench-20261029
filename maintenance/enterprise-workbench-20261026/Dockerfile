FROM monitor-dashboard:local
WORKDIR /dashboard
COPY Dashboard.tsx app/Dashboard.tsx
COPY layout.tsx app/layout.tsx
RUN npm run build
