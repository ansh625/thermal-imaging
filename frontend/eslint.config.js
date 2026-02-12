import js from "@eslint/js";
import globals from "globals";
import reactPlugin from "eslint-plugin-react";
import { defineConfig } from "eslint/config";

export default defineConfig([
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,

      // 🔥 THIS IS THE KEY FIX
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      react: reactPlugin,
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      ...reactPlugin.configs.recommended.rules,

      // React 17+
      "react/react-in-jsx-scope": "off",

      // No prop-types
      "react/prop-types": "off",

      // Optional
      "react/no-unescaped-entities": "off",
      "no-unused-vars": "warn",
    },
  },
]);
