"use client";
import { useEffect, useState } from "react";
import { ModelInfo } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  value: string;
  onChange: (model: string) => void;
  disabled?: boolean;
}

export default function ModelPicker({ value, onChange, disabled }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    fetch(`${API}/api/models`)
      .then((r) => r.json())
      .then((data) => {
        setModels(data);
        if (!value && data.length > 0) onChange(data[0].id);
      });
  }, []);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
    >
      {models.map((m) => (
        <option key={m.id} value={m.id}>
          {m.label}
        </option>
      ))}
    </select>
  );
}
