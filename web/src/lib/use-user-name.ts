"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "boibondhu.name";
const DEFAULT_NAME = "বন্ধু";

export function useUserName() {
  const [userName, setUserName] = useState(DEFAULT_NAME);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setUserName(stored);
      }
    } catch {
      // localStorage can be unavailable (private mode); the default name is fine.
    }
  }, []);

  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === STORAGE_KEY && event.newValue) {
        setUserName(event.newValue);
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const save = useCallback((next: string) => {
    const cleaned = next.trim() || DEFAULT_NAME;
    setUserName(cleaned);
    try {
      window.localStorage.setItem(STORAGE_KEY, cleaned);
    } catch {
      // Ignore persistence failures; the in-memory name still updates.
    }
  }, []);

  return { userName, saveUserName: save };
}
