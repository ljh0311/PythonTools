import React, { useEffect, useState, useMemo } from 'react';

interface FileInfo {
  name: string;
  path: string;
  size: number;
  modified: number;
}

const ViewFilesPage: React.FC = () => {
  const [uploads, setUploads] = useState<FileInfo[]>([]);
  const [results, setResults] = useState<FileInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [sortResultsOrder, setSortResultsOrder] = useState<'desc' | 'asc'>('desc');
  const [sortUploadsOrder, setSortUploadsOrder] = useState<'desc' | 'asc'>('desc');

  useEffect(() => {
    fetch('/api/view_files')
      .then(async res => {
        const text = await res.text();
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        try {
          return JSON.parse(text);
        } catch (err) {
          throw new Error(`Invalid JSON: ${text}`);
        }
      })
      .then(data => {
        if (data.success) {
          setUploads(data.uploads);
          setResults(data.results);
        } else {
          setError(data.error || 'Failed to fetch files');
        }
        setLoading(false);
      })
      .catch(err => {
        setError('Error fetching files: ' + err.message);
        setLoading(false);
      });
  }, []);

  const handleSelect = (path: string) => {
    setSelected(selected =>
      selected.includes(path)
        ? selected.filter(p => p !== path)
        : [...selected, path]
    );
  };

  // Helper function to get modified time in milliseconds
  const getModifiedTime = (file: FileInfo): number => {
    // modified is a Unix timestamp in seconds, convert to milliseconds
    if (typeof file.modified === 'number') {
      // If it's already in milliseconds (>= year 2000 in ms), use as is
      // Otherwise assume it's in seconds and convert
      return file.modified > 946684800000 ? file.modified : file.modified * 1000;
    }
    // If it's a string, parse it
    if (typeof file.modified === 'string') {
      return new Date(file.modified).getTime();
    }
    return 0;
  };

  // Sort results using useMemo to recalculate when results or sort order changes
  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => {
      const at = getModifiedTime(a);
      const bt = getModifiedTime(b);
      return sortResultsOrder === 'asc' ? at - bt : bt - at;
    });
  }, [results, sortResultsOrder]);

  // Sort uploads using useMemo to recalculate when uploads or sort order changes
  const sortedUploads = useMemo(() => {
    return [...uploads].sort((a, b) => {
      const at = getModifiedTime(a);
      const bt = getModifiedTime(b);
      return sortUploadsOrder === 'asc' ? at - bt : bt - at;
    });
  }, [uploads, sortUploadsOrder]);

  const handleDelete = async () => {
    setDeleting(true);
    setError(null);
    try {
      const res = await fetch('/delete_files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_paths: selected })
      });
      const text = await res.text();
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        throw new Error(`Invalid JSON: ${text}`);
      }
      if (data.success) {
        setUploads(u => u.filter(f => !selected.includes(f.path)));
        setResults(r => r.filter(f => !selected.includes(f.path)));
        setSelected([]);
      } else {
        setError(data.message || 'Failed to delete files');
      }
    } catch (err: any) {
      setError('Error deleting files: ' + err.message);
    } finally {
      setDeleting(false);
    }
  };

  const renderFile = (file: FileInfo) => (
    <div className={`file-item p-2 border-bottom d-flex align-items-center position-relative${selected.includes(file.path) ? ' bg-light' : ''}`} key={file.path}>
      <div className="form-check me-2">
        <input className="form-check-input" type="checkbox" checked={selected.includes(file.path)} onChange={() => handleSelect(file.path)} />
      </div>
      {file.name.match(/\.(jpg|jpeg|png|gif|bmp)$/i) ? (
        <img src={file.path} className="preview-image me-3" alt={file.name} style={{ maxWidth: 60, maxHeight: 60, objectFit: 'cover', borderRadius: 6 }} />
      ) : (
        <i className="bi bi-file-earmark-image fs-1 me-3"></i>
      )}
      <div className="flex-grow-1">
        <h6 className="mb-0">{file.name}</h6>
        <small className="text-muted">
          Size: {(file.size / 1024).toFixed(2)} KB<br />
          Modified: {new Date(getModifiedTime(file)).toLocaleString()}
        </small>
      </div>
      <button 
        className="btn btn-sm btn-outline-primary me-1" 
        onClick={() => {
          const modal = document.createElement('div');
          modal.style.position = 'fixed';
          modal.style.top = '0';
          modal.style.left = '0';
          modal.style.width = '100%';
          modal.style.height = '100%';
          modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
          modal.style.display = 'flex';
          modal.style.justifyContent = 'center';
          modal.style.alignItems = 'center';
          modal.style.zIndex = '1000';
          
          const img = document.createElement('img');
          img.src = file.path;
          img.style.maxWidth = '90%';
          img.style.maxHeight = '90%';
          img.style.objectFit = 'contain';
          
          modal.appendChild(img);
          document.body.appendChild(modal);
          
          modal.onclick = () => {
            document.body.removeChild(modal);
          };
        }}
      >
        <i className="bi bi-eye"></i>
      </button>
    </div>

  );

  return (
    <div className="container mt-4">
      {error && <div className="alert alert-danger">{error}</div>}
      {loading ? <div className="text-center">Loading...</div> : (
        <div className="row">
          <div className="col-md-6">
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                  <i className="bi bi-upload me-2"></i>Uploads
                </h5>
                <span className="badge bg-primary">{uploads.length} files</span>
              </div>
              <div className="card-body file-list" style={{ maxHeight: 400, overflowY: 'auto' }}>
                <div className="mb-2 d-flex align-items-center justify-content-between">
                  <div className="d-flex align-items-center">
                    <label htmlFor="bulkSelectUploadsByTime" className="form-label me-2 mb-0">
                      Bulk select:
                    </label>
                    <select
                      id="bulkSelectUploadsByTime"
                      className="form-select form-select-sm w-auto me-3"
                      defaultValue=""
                      onChange={e => {
                        const val = e.target.value;
                        if (!val) return;
                        
                        const now = Date.now();
                        let cutoffMs = 0;
                        
                        // Calculate cutoff time in milliseconds
                        if (val === "1mo") {
                          cutoffMs = now - (30 * 24 * 60 * 60 * 1000); // 30 days
                        } else if (val === "3mo") {
                          cutoffMs = now - (90 * 24 * 60 * 60 * 1000); // 90 days
                        } else if (val === "6mo") {
                          cutoffMs = now - (180 * 24 * 60 * 60 * 1000); // 180 days
                        }
                        
                        // Filter files modified before the cutoff time
                        const toSelect = uploads
                          .filter(f => {
                            const fileModifiedMs = getModifiedTime(f);
                            return fileModifiedMs > 0 && fileModifiedMs < cutoffMs;
                          })
                          .map(f => f.path);
                        
                        // Add to selected, avoiding duplicates
                        setSelected(prev => Array.from(new Set([...prev, ...toSelect])));
                        
                        // Reset select to default
                        e.target.value = "";
                      }}
                    >
                      <option value="">By time...</option>
                      <option value="1mo">More than 1 month ago</option>
                      <option value="3mo">More than 3 months ago</option>
                      <option value="6mo">More than 6 months ago</option>
                    </select>
                  </div>
                  <div className="d-flex align-items-center">
                    <label htmlFor="sortUploads" className="form-label me-2 mb-0">
                      Sort by:
                    </label>
                    <select
                      id="sortUploads"
                      className="form-select form-select-sm w-auto"
                      value={sortUploadsOrder}
                      onChange={e => {
                        setSortUploadsOrder(e.target.value as 'desc' | 'asc');
                      }}
                    >
                      <option value="desc">Newest First</option>
                      <option value="asc">Oldest First</option>
                    </select>
                  </div>
                </div>
                {sortedUploads.length ? (
                  sortedUploads.map(renderFile)
                ) : (
                  <div className="text-center text-muted p-4">
                    <i className="bi bi-inbox fs-1"></i>
                    <p className="mt-2">No files in uploads folder</p>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="col-md-6">
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">
                  <i className="bi bi-images me-2"></i>Results
                </h5>
                <span className="badge bg-primary">{results.length} files</span>
              </div>
              <div className="card-body file-list" style={{ maxHeight: 400, overflowY: 'auto' }}>
                <div className="mb-2 d-flex align-items-center justify-content-between">
                  <div className="d-flex align-items-center">
                    <label htmlFor="bulkSelectByTime" className="form-label me-2 mb-0">
                      Bulk select:
                    </label>
                    <select
                      id="bulkSelectByTime"
                      className="form-select form-select-sm w-auto me-3"
                      defaultValue=""
                      onChange={e => {
                        const val = e.target.value;
                        if (!val) return;
                        
                        const now = Date.now();
                        let cutoffMs = 0;
                        
                        // Calculate cutoff time in milliseconds
                        if (val === "1mo") {
                          cutoffMs = now - (30 * 24 * 60 * 60 * 1000); // 30 days
                        } else if (val === "3mo") {
                          cutoffMs = now - (90 * 24 * 60 * 60 * 1000); // 90 days
                        } else if (val === "6mo") {
                          cutoffMs = now - (180 * 24 * 60 * 60 * 1000); // 180 days
                        }
                        
                        // Filter files modified before the cutoff time
                        const toSelect = results
                          .filter(f => {
                            const fileModifiedMs = getModifiedTime(f);
                            return fileModifiedMs > 0 && fileModifiedMs < cutoffMs;
                          })
                          .map(f => f.path);
                        
                        // Add to selected, avoiding duplicates
                        setSelected(prev => Array.from(new Set([...prev, ...toSelect])));
                        
                        // Reset select to default
                        e.target.value = "";
                      }}
                    >
                      <option value="">By time...</option>
                      <option value="1mo">More than 1 month ago</option>
                      <option value="3mo">More than 3 months ago</option>
                      <option value="6mo">More than 6 months ago</option>
                    </select>
                  </div>
                  <div className="d-flex align-items-center">
                    <label htmlFor="sortResults" className="form-label me-2 mb-0">
                      Sort by:
                    </label>
                    <select
                      id="sortResults"
                      className="form-select form-select-sm w-auto"
                      value={sortResultsOrder}
                      onChange={e => {
                        setSortResultsOrder(e.target.value as 'desc' | 'asc');
                      }}
                    >
                      <option value="desc">Newest First</option>
                      <option value="asc">Oldest First</option>
                    </select>
                  </div>
                </div>
                {sortedResults.length ? (
                  sortedResults.map(renderFile)
                ) : (
                  <div className="text-center text-muted p-4">
                    <i className="bi bi-inbox fs-1"></i>
                    <p className="mt-2">No files in results folder</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="mt-3 text-end">
        <button className="btn btn-danger" onClick={handleDelete} disabled={!selected.length || deleting}>
          <i className="bi bi-trash me-1"></i>Delete Selected ({selected.length})
        </button>
      </div>
    </div>
  );
};

export default ViewFilesPage; 