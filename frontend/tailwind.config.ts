import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg-canvas)",
        surface: "var(--bg-surface)",
        raised: "var(--bg-raised)",
        subtle: "var(--bg-subtle)",
        selected: "var(--bg-selected)",
        accent: {
          DEFAULT: "var(--accent)",
          fg: "var(--accent-fg)",
        },
        border: {
          subtle: "var(--border-subtle)",
          DEFAULT: "var(--border-default)",
          strong: "var(--border-strong)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          inverse: "var(--text-inverse)",
        },
        success: {
          fg: "var(--success-fg)",
          bg: "var(--success-bg)",
        },
        warning: {
          fg: "var(--warning-fg)",
          bg: "var(--warning-bg)",
        },
        danger: {
          fg: "var(--danger-fg)",
          bg: "var(--danger-bg)",
        },
        info: {
          fg: "var(--info-fg)",
          bg: "var(--info-bg)",
        },
        ring: "var(--focus-ring)",
        entity: {
          domain: "var(--entity-domain)",
          subdomain: "var(--entity-subdomain)",
          ip: "var(--entity-ip)",
          technology: "var(--entity-technology)",
          certificate: "var(--entity-certificate)",
          "certificate-stroke": "var(--entity-certificate-stroke)",
          repository: "var(--entity-repository)",
          "cloud-provider": "var(--entity-cloud-provider)",
          organization: "var(--entity-organization)",
          nameserver: "var(--entity-nameserver)",
          "mail-provider": "var(--entity-mail-provider)",
        },
      },
      borderRadius: {
        control: "var(--radius-control)", // 4px
        panel: "var(--radius-panel)",     // 6px
      },
      boxShadow: {
        overlay: "var(--shadow-overlay)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      transitionDuration: {
        fast: "120ms",
        normal: "180ms",
      },
    },
  },
  plugins: [],
};

export default config;
