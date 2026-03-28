#!/usr/bin/env node
/**
 * Auto-generate .graphql operation files from a client-facing schema.
 *
 * Parses the schema, discovers all Query and Mutation fields, and generates
 * typed operations that select all scalar fields + one level of nested objects.
 *
 * Usage:
 *   node scripts/generate-operations.mjs [schema-path] [output-dir]
 *
 * Defaults:
 *   schema-path = graphql/client-schema.graphql
 *   output-dir  = graphql/operations
 */

import { readFileSync, writeFileSync, mkdirSync, readdirSync, unlinkSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { buildSchema } from "graphql";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const schemaPath = process.argv[2] || join(ROOT, "graphql/client-schema.graphql");
const outputDir = process.argv[3] || join(ROOT, "graphql/operations");

// ---------------------------------------------------------------------------
// Parse schema
// ---------------------------------------------------------------------------
const schemaSDL = readFileSync(schemaPath, "utf-8");
const schema = buildSchema(schemaSDL);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Unwrap NonNull / List wrappers to get the named type */
function unwrapType(type) {
  while (type.ofType) type = type.ofType;
  return type;
}

/** Check if a type is a scalar or enum (leaf type) */
function isLeafType(type) {
  const named = unwrapType(type);
  const typeDef = schema.getType(named.name);
  if (!typeDef) return true; // built-in scalars
  const kind = typeDef.astNode?.kind;
  return (
    kind === "ScalarTypeDefinition" ||
    kind === "EnumTypeDefinition" ||
    !typeDef.getFields // scalars don't have getFields
  );
}

/**
 * Build a selection set string for a given GraphQL object type.
 * depth=0: select scalar fields only
 * depth=1: select scalars + one level of nested object scalars
 */
function buildSelectionSet(typeName, depth = 1, visited = new Set(), indentLevel = 2) {
  const typeDef = schema.getType(typeName);
  if (!typeDef || !typeDef.getFields) return "";

  const pad = "  ".repeat(indentLevel);
  const closePad = "  ".repeat(indentLevel - 1);

  // Prevent infinite recursion on circular types
  if (visited.has(typeName)) {
    const fields = typeDef.getFields();
    const scalars = Object.values(fields)
      .filter((f) => isLeafType(f.type))
      .map((f) => `${pad}${f.name}`);
    return scalars.length ? `{\n${scalars.join("\n")}\n${closePad}}` : "{ __typename }";
  }

  visited.add(typeName);
  const fields = typeDef.getFields();
  const lines = [];

  for (const field of Object.values(fields)) {
    const namedType = unwrapType(field.type);

    if (isLeafType(field.type)) {
      lines.push(`${pad}${field.name}`);
    } else if (depth > 0) {
      const nested = buildSelectionSet(namedType.name, depth - 1, new Set(visited), indentLevel + 1);
      if (nested) {
        lines.push(`${pad}${field.name} ${nested}`);
      }
    }
  }

  if (lines.length === 0) return "{ __typename }";

  return `{\n${lines.join("\n")}\n${closePad}}`;
}

/**
 * Build the variable definitions and argument pass-through for a field.
 * e.g. ($id: Int!, $input: UpdateTodoInput!) and (id: $id, input: $input)
 */
function buildArgs(field) {
  if (!field.args || field.args.length === 0) return { varDefs: "", callArgs: "" };

  const varDefs = field.args
    .map((a) => `$${a.name}: ${a.type}`)
    .join(", ");

  const callArgs = field.args
    .map((a) => `${a.name}: $${a.name}`)
    .join(", ");

  return { varDefs: `(${varDefs})`, callArgs: `(${callArgs})` };
}

/** Convert a field name to PascalCase operation name */
function toPascalCase(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ---------------------------------------------------------------------------
// Generate operations
// ---------------------------------------------------------------------------

function generateOperations(rootTypeName, operationType) {
  const rootType = schema.getType(rootTypeName);
  if (!rootType || !rootType.getFields) return [];

  const fields = rootType.getFields();
  const operations = [];

  for (const field of Object.values(fields)) {
    const opName = toPascalCase(field.name);
    const returnType = unwrapType(field.type);
    const { varDefs, callArgs } = buildArgs(field);

    let selectionSet = "";
    if (!isLeafType(field.type)) {
      selectionSet = " " + buildSelectionSet(returnType.name);
    }

    const op = `${operationType}${varDefs ? ` ${opName}${varDefs}` : ` ${opName}`} {
  ${field.name}${callArgs}${selectionSet}
}`;

    operations.push({ name: opName, content: op });
  }

  return operations;
}

// ---------------------------------------------------------------------------
// Write files
// ---------------------------------------------------------------------------

// Clean previously generated files (only files with the AUTO-GENERATED header)
mkdirSync(outputDir, { recursive: true });
const GENERATED_MARKER = "# AUTO-GENERATED";

for (const file of readdirSync(outputDir)) {
  if (file.endsWith(".graphql")) {
    const content = readFileSync(join(outputDir, file), "utf-8");
    if (content.startsWith(GENERATED_MARKER)) {
      unlinkSync(join(outputDir, file));
    }
  }
}

const queryOps = generateOperations("Query", "query");
const mutationOps = generateOperations("Mutation", "mutation");

// Group by file: queries.graphql and mutations.graphql
function writeOpsFile(filename, ops) {
  if (ops.length === 0) return;

  const header = `${GENERATED_MARKER} by scripts/generate-operations.mjs
# Do not edit manually. Regenerate with: npm run generate:ops\n\n`;

  const content = header + ops.map((o) => o.content).join("\n\n") + "\n";
  const filePath = join(outputDir, filename);
  writeFileSync(filePath, content, "utf-8");
  console.log(`  -> ${filePath} (${ops.length} operations)`);
}

console.log("Generating GraphQL operations from schema...");
writeOpsFile("queries.graphql", queryOps);
writeOpsFile("mutations.graphql", mutationOps);
console.log("Done.");
