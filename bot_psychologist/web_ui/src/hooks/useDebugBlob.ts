import { useState, useCallback } from 'react';

export function useDebugBlob() {
  const [blobs, setBlobs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const fetchBlob = useCallback(async (blobId: string) => {
    if (!blobId || blobs[blobId] || loading[blobId]) return;
    setLoading((prev) => ({ ...prev, [blobId]: true }));
    try {
      const res = await fetch(`/api/debug/blob/${blobId}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Blob not found');
      const data = await res.json();
      setBlobs((prev) => ({ ...prev, [blobId]: data.content }));
    } catch {
      setBlobs((prev) => ({ ...prev, [blobId]: '[Ошибка загрузки]' }));
    } finally {
      setLoading((prev) => ({ ...prev, [blobId]: false }));
    }
  }, [blobs, loading]);

  return { blobs, loading, fetchBlob };
}
