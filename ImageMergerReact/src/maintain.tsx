import React, { useState, useMemo, useEffect, useRef } from 'react';
import { formatFileSize, formatTimestamp } from './format.ts';

interface TestResult {
  name: string;
  success: boolean;
  duration?: number;
  error?: string;
  image?: string;
}

interface StorageInfo {
  used: number;
  total: number;
}

interface CleanupResults {
  moved: number;
  errors: number;
  freed: number;
  storage?: StorageInfo;
  movedFiles?: string[];
  timestamp?: number;
}

interface TestRun {
  id: string;
  timestamp: number;
  results: TestResult[];
  passed: number;
  failed: number;
}

const MaintenancePage: React.FC = () => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [testHistory, setTestHistory] = useState<TestRun[]>([]);
  const [cleanupResults, setCleanupResults] = useState<CleanupResults | null>(null);
  const [loadingTest, setLoadingTest] = useState(false);
  const [loadingCleanup, setLoadingCleanup] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [cleanupError, setCleanupError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    testResults: true,
    testHistory: false,
    cleanupDetails: false,
    systemInfo: false
  });
  const [testFilter, setTestFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [testSortBy, setTestSortBy] = useState<'name' | 'duration' | 'status'>('name');
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  const [confirmConfig, setConfirmConfig] = useState<{ message: string; onConfirm: () => void } | null>(null);
  const [systemStorage, setSystemStorage] = useState<StorageInfo | null>(null);
  const [loadingStorage, setLoadingStorage] = useState(false);
  const lightboxCloseRef = useRef<HTMLButtonElement>(null);

  const getErrorMessage = (err: unknown): string =>
    err instanceof Error ? err.message : String(err);

  const closeLightbox = () => setLightboxImage(null);

  useEffect(() => {
    if (!lightboxImage) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeLightbox();
    };
    window.addEventListener('keydown', onKeyDown);
    lightboxCloseRef.current?.focus();
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [lightboxImage]);

  const fetchStorageInfo = async () => {
    setLoadingStorage(true);
    try {
      const response = await fetch('/storage_info');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.success && data.storage) setSystemStorage(data.storage as StorageInfo);
    } catch {
      setSystemStorage(null);
    } finally {
      setLoadingStorage(false);
    }
  };

  useEffect(() => {
    fetchStorageInfo();
  }, []);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleRunTests = async () => {
    setLoadingTest(true);
    setTestError(null);
    setTestResults([]);
    try {
      const response = await fetch('/run_tests');
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      let data;
      try {
        data = await response.json();
      } catch (err) {
        const text = await response.text();
        throw new Error(`Invalid JSON: ${text}`);
      }
      if (data.success && Array.isArray(data.results)) {
        const results = data.results as TestResult[];
        setTestResults(results);
        // Add to history
        const testRun: TestRun = {
          id: Date.now().toString(),
          timestamp: Date.now(),
          results,
          passed: results.filter(r => r.success).length,
          failed: results.filter(r => !r.success).length
        };
        setTestHistory(prev => [testRun, ...prev].slice(0, 10)); // Keep last 10 runs
      } else {
        setTestError(data.error || 'Failed to run tests');
      }
    } catch (err: unknown) {
      setTestError('Error running tests: ' + getErrorMessage(err));
    } finally {
      setLoadingTest(false);
    }
  };

  const handleRunCleanup = async () => {
    setLoadingCleanup(true);
    setCleanupError(null);
    setCleanupResults(null);
    try {
      const response = await fetch('/run_cleanup');
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      let data;
      try {
        data = await response.json();
      } catch (err) {
        const text = await response.text();
        throw new Error(`Invalid JSON: ${text}`);
      }
      if (data.success) {
        // API returns freed in MB, storage.used/total in MB
        setCleanupResults({
          ...data,
          timestamp: Date.now()
        });
      } else {
        setCleanupError(data.error || 'Failed to run cleanup');
      }
    } catch (err: unknown) {
      setCleanupError('Error running cleanup: ' + getErrorMessage(err));
    } finally {
      setLoadingCleanup(false);
    }
  };

  const handleExportTests = () => {
    if (testResults.length === 0) return;
    const dataStr = JSON.stringify(testResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `test-results-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleClearTests = () => {
    setConfirmConfig({
      message: 'Clear all test results?',
      onConfirm: () => {
        setTestResults([]);
        setTestError(null);
        setConfirmConfig(null);
      }
    });
  };

  const handleRunCleanupClick = () => {
    setConfirmConfig({
      message: 'Are you sure you want to run cleanup? This action cannot be undone.',
      onConfirm: () => {
        setConfirmConfig(null);
        handleRunCleanup();
      }
    });
  };

  const handleClearCleanup = () => {
    setCleanupResults(null);
    setCleanupError(null);
  };

  // Filter and sort test results
  const filteredAndSortedTests = useMemo(() => {
    let filtered = [...testResults];
    
    // Apply filter
    if (testFilter === 'passed') {
      filtered = filtered.filter(r => r.success);
    } else if (testFilter === 'failed') {
      filtered = filtered.filter(r => !r.success);
    }
    
    // Apply sort
    filtered.sort((a, b) => {
      if (testSortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (testSortBy === 'duration') {
        const aDur = a.duration || 0;
        const bDur = b.duration || 0;
        return bDur - aDur; // Descending
      } else { // status
        if (a.success === b.success) return 0;
        return a.success ? 1 : -1; // Failed first
      }
    });
    
    return filtered;
  }, [testResults, testFilter, testSortBy]);

  const passed = testResults.filter(r => r.success).length;
  const failed = testResults.filter(r => !r.success).length;
  const totalDuration = testResults.reduce((sum, r) => sum + (r.duration || 0), 0);
  const displayStorage = systemStorage ?? cleanupResults?.storage;

  return (
    <div className="container my-5">
      <div className="row g-4">
        <div className="col-lg-6">
          <div className="card shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
              <h5 className="mb-0 d-flex align-items-center">
                <i className="bi bi-check-circle me-2 text-primary"></i>
                Test Results
              </h5>
              <div className="d-flex gap-2">
                {testResults.length > 0 && (
                  <>
                    <button 
                      className="btn btn-outline-secondary btn-sm" 
                      onClick={handleExportTests}
                      title="Export test results"
                    >
                      <i className="bi bi-download me-1"></i>Export
                    </button>
                    <button 
                      className="btn btn-outline-danger btn-sm" 
                      onClick={handleClearTests}
                      title="Clear test results"
                    >
                      <i className="bi bi-x-circle me-1"></i>Clear
                    </button>
                  </>
                )}
                <button
                  className="btn btn-primary btn-sm d-flex align-items-center"
                  onClick={handleRunTests}
                  disabled={loadingTest}
                  aria-busy={loadingTest}
                >
                  <i className={`bi ${loadingTest ? 'bi-arrow-repeat' : 'bi-play-fill'} me-2`}></i>
                  {loadingTest ? 'Running...' : 'Run Tests'}
                </button>
              </div>
            </div>
            <div className="card-body">
              {testError && (
                <div className="alert alert-danger d-flex align-items-center justify-content-between">
                  <div className="d-flex align-items-center">
                    <i className="bi bi-exclamation-triangle-fill me-2"></i>
                    <span>{testError}</span>
                  </div>
                  <button 
                    className="btn btn-sm btn-outline-danger" 
                    onClick={() => setTestError(null)}
                    title="Dismiss error"
                  >
                    <i className="bi bi-x"></i>
                  </button>
                </div>
              )}
              {loadingTest && (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="mt-2 text-muted">Running tests...</p>
                </div>
              )}
              {testResults.length > 0 && (
                <div>
                  <div className="mb-3 d-flex flex-wrap gap-2 align-items-center">
                    <span className="badge bg-success d-flex align-items-center">
                      <i className="bi bi-check-circle-fill me-1"></i>
                      Passed: {passed}
                    </span>
                    <span className="badge bg-danger d-flex align-items-center">
                      <i className="bi bi-x-circle-fill me-1"></i>
                      Failed: {failed}
                    </span>
                    <span className="badge bg-info d-flex align-items-center">
                      <i className="bi bi-clock me-1"></i>
                      Total: {totalDuration.toFixed(2)}s
                    </span>
                  </div>
                  <div className="mb-3 d-flex gap-2 align-items-center">
                    <label className="form-label mb-0 small">Filter:</label>
                    <select 
                      className="form-select form-select-sm w-auto" 
                      value={testFilter}
                      onChange={(e) => setTestFilter(e.target.value as 'all' | 'passed' | 'failed')}
                    >
                      <option value="all">All</option>
                      <option value="passed">Passed</option>
                      <option value="failed">Failed</option>
                    </select>
                    <label className="form-label mb-0 small ms-2">Sort:</label>
                    <select 
                      className="form-select form-select-sm w-auto" 
                      value={testSortBy}
                      onChange={(e) => setTestSortBy(e.target.value as 'name' | 'duration' | 'status')}
                    >
                      <option value="name">Name</option>
                      <option value="duration">Duration</option>
                      <option value="status">Status</option>
                    </select>
                  </div>
                  <ul className="list-group list-group-flush">
                    {filteredAndSortedTests.map((r, i) => (
                      <li key={`${r.name}-${r.duration ?? 0}-${i}`} className={`list-group-item ${r.success ? 'list-group-item-success' : 'list-group-item-danger'}`}>
                        <div className="d-flex justify-content-between align-items-center">
                          <span className="fw-medium">{r.name}</span>
                          <span className="d-flex align-items-center">
                            {r.success ? 
                              <i className="bi bi-check-circle-fill text-success"></i> : 
                              <i className="bi bi-x-circle-fill text-danger"></i>
                            }
                            {r.duration && (
                              <span className="ms-2 text-muted small">
                                <i className="bi bi-clock me-1"></i>
                                {r.duration.toFixed(2)}s
                              </span>
                            )}
                          </span>
                        </div>
                        {r.error && (
                          <div className="text-danger small mt-2 d-flex align-items-start">
                            <i className="bi bi-exclamation-circle me-1 mt-1"></i>
                            <span className="flex-grow-1">{r.error}</span>
                          </div>
                        )}
                        {r.image && (
                          <div className="mt-2">
                            <img
                              src={r.image}
                              alt={`Test result for ${r.name}`}
                              className="img-fluid rounded shadow-sm"
                              style={{ maxHeight: '200px', width: 'auto', cursor: 'pointer' }}
                              onClick={() => setLightboxImage(r.image!)}
                            />
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                  {filteredAndSortedTests.length === 0 && (
                    <div className="alert alert-warning mt-3">
                      <i className="bi bi-info-circle me-2"></i>
                      No tests match the current filter.
                    </div>
                  )}
                </div>
              )}
              {testResults.length === 0 && !loadingTest && !testError && (
                <div className="alert alert-info d-flex align-items-center">
                  <i className="bi bi-info-circle-fill me-2"></i>
                  Test results will appear here.
                </div>
              )}
              {testHistory.length > 0 && (
                <div className="mt-4">
                  <button
                    className="btn btn-link p-0 text-decoration-none"
                    onClick={() => toggleSection('testHistory')}
                  >
                    <i className={`bi bi-chevron-${expandedSections.testHistory ? 'down' : 'right'} me-1`}></i>
                    Test History ({testHistory.length})
                  </button>
                  {expandedSections.testHistory && (
                    <div className="mt-2">
                      {testHistory.map((run) => (
                        <div key={run.id} className="small text-muted mb-1">
                          {formatTimestamp(run.timestamp)} - {run.passed} passed, {run.failed} failed
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card shadow-sm">
            <div className="card-header bg-light d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                <i className="bi bi-tools me-2"></i>
                Maintenance Tools
              </h5>
              <div className="d-flex gap-2">
                {cleanupResults && (
                  <button 
                    className="btn btn-outline-secondary btn-sm" 
                    onClick={handleClearCleanup}
                    title="Clear cleanup results"
                  >
                    <i className="bi bi-x-circle me-1"></i>Clear
                  </button>
                )}
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleRunCleanupClick}
                  disabled={loadingCleanup}
                  title="Run system cleanup to free up space"
                  aria-busy={loadingCleanup}
                >
                  <i className="bi bi-trash me-2"></i>
                  {loadingCleanup ? (
                    <span>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Cleaning...
                    </span>
                  ) : 'Run Cleanup'}
                </button>
              </div>
            </div>
            <div className="card-body">
              {cleanupError && (
                <div className="alert alert-danger d-flex align-items-center justify-content-between">
                  <div className="d-flex align-items-center">
                    <i className="bi bi-exclamation-triangle-fill me-2"></i>
                    <span>{cleanupError}</span>
                  </div>
                  <button 
                    className="btn btn-sm btn-outline-danger" 
                    onClick={() => setCleanupError(null)}
                    title="Dismiss error"
                  >
                    <i className="bi bi-x"></i>
                  </button>
                </div>
              )}
              {loadingCleanup && (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="mt-2 text-muted">Running cleanup...</p>
                </div>
              )}
              {cleanupResults && (
                <div>
                  {cleanupResults.timestamp && (
                    <div className="text-muted small mb-2">
                      <i className="bi bi-clock me-1"></i>
                      Last run: {formatTimestamp(cleanupResults.timestamp)}
                    </div>
                  )}
                  <div className="mb-3">
                    <div className="d-flex flex-wrap gap-2 align-items-center">
                      <span className="badge bg-primary p-2">
                        <i className="bi bi-arrow-right-circle me-1"></i>
                        Moved: {cleanupResults.moved}
                      </span>
                      <span className="badge bg-danger p-2">
                        <i className="bi bi-exclamation-triangle me-1"></i>
                        Errors: {cleanupResults.errors}
                      </span>
                      <span className="badge bg-success p-2">
                        <i className="bi bi-check-circle me-1"></i>
                        Freed: {formatFileSize(cleanupResults.freed * 1024 * 1024)}
                      </span>
                    </div>
                  </div>
                  {cleanupResults.storage && (
                    <>
                      <div className="progress mb-2" style={{ height: '25px' }}>
                        <div 
                          className="progress-bar" 
                          role="progressbar" 
                          style={{ 
                            width: `${Math.min((cleanupResults.storage.used / cleanupResults.storage.total) * 100, 100)}%`,
                            backgroundColor: (cleanupResults.storage.used / cleanupResults.storage.total) > 0.9 ? '#dc3545' : 
                                           (cleanupResults.storage.used / cleanupResults.storage.total) > 0.7 ? '#ffc107' : '#0d6efd'
                          }}
                          aria-valuenow={cleanupResults.storage.used} 
                          aria-valuemin={0} 
                          aria-valuemax={cleanupResults.storage.total}
                        >
                          {Math.round((cleanupResults.storage.used / cleanupResults.storage.total) * 100)}%
                        </div>
                      </div>
                      <div className="d-flex justify-content-between text-muted small mb-3">
                        <span>Used: {formatFileSize(cleanupResults.storage.used * 1024 * 1024)}</span>
                        <span>Total: {formatFileSize(cleanupResults.storage.total * 1024 * 1024)}</span>
                        <span>Free: {formatFileSize((cleanupResults.storage.total - cleanupResults.storage.used) * 1024 * 1024)}</span>
                      </div>
                    </>
                  )}
                  {cleanupResults.movedFiles && cleanupResults.movedFiles.length > 0 && (
                    <div className="mt-4">
                      <button
                        className="btn btn-link p-0 text-decoration-none"
                        onClick={() => toggleSection('cleanupDetails')}
                      >
                        <i className={`bi bi-chevron-${expandedSections.cleanupDetails ? 'down' : 'right'} me-1`}></i>
                        Moved Files ({cleanupResults.movedFiles.length})
                      </button>
                      {expandedSections.cleanupDetails && (
                        <div className="list-group mt-2" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                          {cleanupResults.movedFiles.map((file, index) => (
                            <div key={index} className="list-group-item list-group-item-action">
                              <div className="d-flex align-items-center">
                                <i className="bi bi-file-earmark me-2 text-primary"></i>
                                <small className="text-truncate">{file}</small>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
              {!cleanupResults && !loadingCleanup && !cleanupError && (
                <div className="alert alert-info d-flex align-items-center">
                  <i className="bi bi-info-circle-fill me-2"></i>
                  Cleanup stats and results will appear here.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="row g-4 mt-2">
        <div className="col-12">
          <div className="card shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
              <h5 className="mb-0 d-flex align-items-center">
                <i className="bi bi-info-circle me-2 text-info"></i>
                System Information
              </h5>
              <button
                className="btn btn-sm btn-outline-primary"
                onClick={fetchStorageInfo}
                disabled={loadingStorage}
                aria-busy={loadingStorage}
              >
                {loadingStorage ? (
                  <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                ) : (
                  <i className="bi bi-arrow-clockwise me-1"></i>
                )}
                {loadingStorage ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-6">
                  <h6 className="mb-3">
                    <i className="bi bi-folder me-2"></i>Storage Overview
                  </h6>
                  {displayStorage ? (
                    <div>
                      <div className="mb-2">
                        <small className="text-muted">Total Storage</small>
                        <div className="fw-bold">{formatFileSize(displayStorage.total * 1024 * 1024)}</div>
                      </div>
                      <div className="mb-2">
                        <small className="text-muted">Used Storage</small>
                        <div className="fw-bold text-warning">{formatFileSize(displayStorage.used * 1024 * 1024)}</div>
                      </div>
                      <div className="mb-2">
                        <small className="text-muted">Free Storage</small>
                        <div className="fw-bold text-success">{formatFileSize((displayStorage.total - displayStorage.used) * 1024 * 1024)}</div>
                      </div>
                      <div className="mb-2">
                        <small className="text-muted">Usage Percentage</small>
                        <div className="fw-bold">
                          {Math.round((displayStorage.used / displayStorage.total) * 100)}%
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-muted small">
                      {loadingStorage ? 'Loading...' : 'Click Refresh to load storage information'}
                    </div>
                  )}
                </div>
                <div className="col-md-6">
                  <h6 className="mb-3">
                    <i className="bi bi-activity me-2"></i>Quick Stats
                  </h6>
                  <div className="d-flex flex-column gap-2">
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Test Runs:</span>
                      <span className="fw-bold">{testHistory.length}</span>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Total Tests:</span>
                      <span className="fw-bold">{testResults.length}</span>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Last Test Run:</span>
                      <span className="fw-bold">
                        {testHistory.length > 0 ? formatTimestamp(testHistory[0].timestamp) : 'Never'}
                      </span>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Last Cleanup:</span>
                      <span className="fw-bold">
                        {cleanupResults?.timestamp ? formatTimestamp(cleanupResults.timestamp) : 'Never'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {confirmConfig && (
        <div className="modal show d-block" tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="confirmModalTitle" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title" id="confirmModalTitle">Confirm</h5>
                <button type="button" className="btn-close" aria-label="Close" onClick={() => setConfirmConfig(null)} />
              </div>
              <div className="modal-body">{confirmConfig.message}</div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setConfirmConfig(null)}>Cancel</button>
                <button type="button" className="btn btn-primary" onClick={() => confirmConfig.onConfirm()}>Confirm</button>
              </div>
            </div>
          </div>
        </div>
      )}
      {lightboxImage && (
        <div
          className="modal show d-block"
          style={{ background: 'rgba(0,0,0,0.9)' }}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="Image preview"
          onClick={closeLightbox}
        >
          <div className="modal-dialog modal-dialog-centered modal-xl mw-100 h-100 m-0" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content bg-transparent border-0">
              <div className="modal-header border-0 pb-0">
                <button
                  ref={lightboxCloseRef}
                  type="button"
                  className="btn-close btn-close-white ms-auto"
                  aria-label="Close"
                  onClick={closeLightbox}
                />
              </div>
              <div className="modal-body d-flex justify-content-center align-items-center pt-0">
                <img
                  src={lightboxImage}
                  alt="Enlarged test result"
                  style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MaintenancePage; 