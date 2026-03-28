import type { CodegenConfig } from "@graphql-codegen/cli";

const config: CodegenConfig = {
  schema: "graphql/client-schema.graphql",
  documents: "graphql/operations/**/*.graphql",
  generates: {
    "generated/typescript/sdk.ts": {
      plugins: [
        "typescript",
        "typescript-operations",
        "typescript-generic-sdk",
      ],
      config: {
        // Use branded scalars for type safety
        scalars: {
          Int: "number",
          Float: "number",
          String: "string",
          Boolean: "boolean",
          ID: "string",
        },
        // SDK config
        rawRequest: false,
        // Use 'pick' for cleaner types
        preResolveTypes: true,
        // Only export what's needed
        onlyOperationTypes: false,
      },
    },
  },
};

export default config;
