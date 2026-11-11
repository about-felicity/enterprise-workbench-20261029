FROM monitor-dashboard:local
COPY app/ /dashboard/app/
COPY public/ /dashboard/public/
COPY tests/ /dashboard/tests/
COPY scripts/ /dashboard/scripts/
WORKDIR /dashboard
RUN node scripts/configure-http-client.mjs && (node -e 'process.exit(require("undici/package.json").version === require("./package.json").dependencies.undici ? 0 : 1)' || npm install --ignore-scripts --no-audit --no-fund)
RUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs tests/video-proxy.test.mjs
RUN node --test tests/rendered-html.test.mjs
RUN npm run build
