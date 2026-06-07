import { defineConfig } from 'openapi-typescript-codegen';
export default defineConfig({
  input: '../../contracts/openapi/gateway-public.v1.yaml',
  output: 'src/shared/api/generated',
  client: 'fetch',
});
