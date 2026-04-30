export type ReportLocation = {
  lat: number;
  lng: number;
  city: string;
  risk: "low" | "medium" | "high";
  reports: number;
  incident: string;
};

type HotspotsResponse =
  | { success: true; data: ReportLocation[] }
  | { success: false; message?: string };

const API_BASE =
  (import.meta as any).env?.VITE_HOTSPOT_BACKEND_BASE_URL || "";

export async function fetchHotspots(): Promise<ReportLocation[]> {
  const token = localStorage.getItem("smartshield_token");
  const res = await fetch(`${API_BASE}/api/hotspots`, {
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
      "Content-Type": "application/json",
    },
    credentials: "include",
  });
  if (res.status === 401) {
    localStorage.removeItem("smartshield_token");
    localStorage.removeItem("smartshield_user");
    throw new Error("Unauthorized");
  }
  const data: HotspotsResponse = await res.json();
  if ((data as any).success) return (data as any).data || [];
  throw new Error((data as any).message || `API error: ${res.status}`);
}

