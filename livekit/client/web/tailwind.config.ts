import type { Config } from "tailwindcss";

const colors = require("tailwindcss/colors");

const sambanova = {
  "accent-bg": "#663399",
};

const customColors = {
  sambanova,
};

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      black: colors.black,
      white: colors.white,
      gray: colors.neutral,
      ...colors,
      ...customColors,
    },
    extend: {
      borderRadius: {
        sm: "calc(var(--radius) - 4px)",
        md: "calc(var(--radius) - 2px)",
        lg: "var(--radius)",
      },
    },
  },
} satisfies Config;

export default config;
