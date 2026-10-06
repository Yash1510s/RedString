/**
 * Single source of truth for entity colours, Cytoscape shapes, sizes, and labels
 * strictly obeying UI_SPEC.md §3.3 using the Okabe-Ito colour-blind safe palette.
 */

export interface EntityStyleConfig {
  type: string;
  label: string;
  color: string;
  borderColor?: string;
  shape:
    | "ellipse"
    | "rectangle"
    | "round-rectangle"
    | "diamond"
    | "hexagon"
    | "triangle"
    | "octagon"
    | "tag"
    | "barrel";
  width: number;
  height: number;
}

export const ENTITY_STYLES: Record<string, EntityStyleConfig> = {
  domain: {
    type: "domain",
    label: "Root Domain",
    color: "#0072B2",
    shape: "ellipse",
    width: 44,
    height: 44,
  },
  subdomain: {
    type: "subdomain",
    label: "Subdomain",
    color: "#56B4E9",
    shape: "ellipse",
    width: 24,
    height: 24,
  },
  ip: {
    type: "ip",
    label: "IP Address",
    color: "#E69F00",
    shape: "rectangle",
    width: 24,
    height: 24,
  },
  technology: {
    type: "technology",
    label: "Technology",
    color: "#009E73",
    shape: "round-rectangle",
    width: 28,
    height: 20,
  },
  certificate: {
    type: "certificate",
    label: "Certificate",
    color: "#F0E442",
    borderColor: "#8A7F00",
    shape: "diamond",
    width: 24,
    height: 24,
  },
  repository: {
    type: "repository",
    label: "Repository",
    color: "#CC79A7",
    shape: "hexagon",
    width: 24,
    height: 24,
  },
  cloud_provider: {
    type: "cloud_provider",
    label: "Cloud Provider",
    color: "#D55E00",
    shape: "triangle",
    width: 24,
    height: 24,
  },
  organization: {
    type: "organization",
    label: "Organization",
    color: "#999999",
    shape: "octagon",
    width: 22,
    height: 22,
  },
  nameserver: {
    type: "nameserver",
    label: "Nameserver",
    color: "#999999",
    shape: "tag",
    width: 22,
    height: 22,
  },
  mail_provider: {
    type: "mail_provider",
    label: "Mail Provider",
    color: "#999999",
    shape: "barrel",
    width: 22,
    height: 22,
  },
};

export function getEntityStyle(type: string): EntityStyleConfig {
  const normalized = type.toLowerCase();
  return (
    ENTITY_STYLES[normalized] || {
      type: normalized,
      label: type,
      color: "#999999",
      shape: "ellipse",
      width: 22,
      height: 22,
    }
  );
}
