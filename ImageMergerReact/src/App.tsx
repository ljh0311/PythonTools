import React, { useState, useRef, useEffect, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import MaintenancePage from './maintain.tsx';
import ViewFilesPage from './viewfiles.tsx';

const App: React.FC = () => (
  <Router>
    <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
      <div className="container">
        <Link className="navbar-brand d-flex align-items-center" to="/">
          <i className="bi bi-images me-2"></i>
          <span>Image Merger</span>
        </Link>
        <div className="collapse navbar-collapse">
          <ul className="navbar-nav ms-auto flex-row gap-2">
            <li className="nav-item">
              <Link to="/maintenance" className="nav-link d-flex align-items-center">
                <i className="bi bi-tools me-1"></i> Maintenance
              </Link>
            </li>
            <li className="nav-item">
              <Link to="/files" className="nav-link d-flex align-items-center">
                <i className="bi bi-folder2-open me-1"></i> View Files
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    <Routes>
      <Route path="/" element={<MainApp />} />
      <Route path="/maintenance" element={<MaintenancePage />} />
      <Route path="/files" element={<ViewFilesPage />} />
    </Routes>
  </Router>
);

const MainApp: React.FC = () => {
  const [files, setFiles] = useState<FileList | null>(null);
  // Basic settings
  const [threshold, setThreshold] = useState(0.7);
  const [alpha, setAlpha] = useState(0.5);
  // Blend mode
  const [blendMode, setBlendMode] = useState<string>('feature_aligned');
  // Feature detection
  const [useOrb, setUseOrb] = useState(false);
  const [ransacThreshold, setRansacThreshold] = useState(5.0);
  const [featureCount, setFeatureCount] = useState(1000);
  const [matchRatio, setMatchRatio] = useState(0.75);
  const [minMatches, setMinMatches] = useState(4);
  // Manual features
  const [manualFeatures, setManualFeatures] = useState(false);
  // Output options
  const [autoCrop, setAutoCrop] = useState(false);
  const [outputSize, setOutputSize] = useState<string>('original');
  const [outputQuality, setOutputQuality] = useState(95);
  const [outputFormat, setOutputFormat] = useState<string>('png');
  // UI state
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualStep, setManualStep] = useState<'img1' | 'img2'>('img1');
  const [manualPairIdx, setManualPairIdx] = useState(0);
  const [multiManualPoints, setMultiManualPoints] = useState<{ img1: [number, number][], img2: [number, number][] }[]>([]);
  const [, setImageLoaded] = useState(false);
  const [mergeStats, setMergeStats] = useState<{ matches?: number; processingTime?: number } | null>(null);
  // Scan for matches state
  const [scanResult, setScanResult] = useState<{
    pairs: { indices: [number, number]; match_count: number }[];
    groups: { indices: number[] }[];
    image_names: string[];
  } | null>(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [mergeIndicesLoading, setMergeIndicesLoading] = useState<number[] | null>(null);
  // Previews for all pairs/groups (key = indices.join(','), value = result_image URL)
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({});
  const [previewAllLoading, setPreviewAllLoading] = useState(false);
  const [currentPreviewIndices, setCurrentPreviewIndices] = useState<number[] | null>(null);
  // Track how current result was produced so we can re-merge with same inputs
  const [lastMergedAs, setLastMergedAs] = useState<'all' | 'indices' | null>(null);
  const [lastMergedIndices, setLastMergedIndices] = useState<number[] | null>(null);
  // Feedback modal state
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  const [adjustingConfig, setAdjustingConfig] = useState(false);
  // Changes display modal state
  const [showChangesModal, setShowChangesModal] = useState(false);
  const [configChanges, setConfigChanges] = useState<Array<{
    key: string;
    label: string;
    oldValue: any;
    newValue: any;
  }>>([]);
  const [pendingAdjustedConfig, setPendingAdjustedConfig] = useState<any>(null);
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    basicSettings: true,
    blendMode: false,
    featureDetection: false,
    outputOptions: false
  });
  const img1Ref = useRef<HTMLImageElement>(null);
  const img2Ref = useRef<HTMLImageElement>(null);

  // Expand Feature Detection when scan results exist so users can tweak and re-scan
  useEffect(() => {
    if (scanResult && ((scanResult.groups?.length ?? 0) > 0 || scanResult.pairs.length > 0)) {
      setExpandedSections(prev => ({ ...prev, featureDetection: true }));
    }
  }, [scanResult]);

  // Memoize object URLs for selected images strip and revoke on cleanup
  const selectedImagePreviews = useMemo(() => {
    if (!files || files.length === 0) return [];
    return Array.from(files).map((file, idx) => {
      const f = file as File;
      const name = f.name || `Image ${idx + 1}`;
      return {
        url: URL.createObjectURL(f),
        name,
        shortName: name.length > 12 ? name.slice(0, 10) + '…' : name,
        index: idx + 1
      };
    });
  }, [files]);
  useEffect(() => {
    return () => {
      selectedImagePreviews.forEach(p => URL.revokeObjectURL(p.url));
    };
  }, [selectedImagePreviews]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(e.target.files);
      setScanResult(null);
    }
  };

  const handleManualModalOpen = () => {
    setManualStep('img1');
    setManualPairIdx(0);
    setShowManualModal(true);
  };

  const handleManualModalClose = () => {
    setShowManualModal(false);
  };

  // Preset configurations
  const applyPreset = (preset: 'quick' | 'balanced' | 'high_quality' | 'night_mode') => {
    switch (preset) {
      case 'quick':
        setThreshold(0.6);
        setAlpha(0.5);
        setBlendMode('feature_aligned');
        setUseOrb(false);
        setRansacThreshold(3.0);
        setFeatureCount(500);
        setMatchRatio(0.7);
        setMinMatches(4);
        setAutoCrop(true);
        setOutputSize('original');
        setOutputQuality(85);
        break;
      case 'balanced':
        setThreshold(0.7);
        setAlpha(0.5);
        setBlendMode('feature_aligned');
        setUseOrb(false);
        setRansacThreshold(5.0);
        setFeatureCount(1000);
        setMatchRatio(0.75);
        setMinMatches(4);
        setAutoCrop(true);
        setOutputSize('original');
        setOutputQuality(95);
        break;
      case 'high_quality':
        setThreshold(0.8);
        setAlpha(0.5);
        setBlendMode('multi_band');
        setUseOrb(false);
        setRansacThreshold(5.0);
        setFeatureCount(2000);
        setMatchRatio(0.8);
        setMinMatches(8);
        setAutoCrop(true);
        setOutputSize('original');
        setOutputQuality(100);
        break;
      case 'night_mode':
        setThreshold(0.6);
        setAlpha(0.5);
        setBlendMode('feature_aligned');
        setUseOrb(true);
        setRansacThreshold(4.0);
        setFeatureCount(1500);
        setMatchRatio(0.7);
        setMinMatches(4);
        setAutoCrop(true);
        setOutputSize('original');
        setOutputQuality(95);
        break;
    }
  };




  const handleMerge = async () => {
    if (!files || files.length < 2) {
      setError('Please upload at least 2 images.');
      return;
    }
    if (manualFeatures) {
      handleManualModalOpen();
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('images', file as Blob);
    });
    formData.append('blend_mode', blendMode);
    formData.append('threshold', threshold.toString());
    formData.append('use_orb', useOrb.toString());
    formData.append('alpha', alpha.toString());
    formData.append('ransac_threshold', ransacThreshold.toString());
    formData.append('feature_count', featureCount.toString());
    formData.append('match_ratio', matchRatio.toString());
    formData.append('min_matches', minMatches.toString());
    formData.append('auto_crop', autoCrop.toString());
    formData.append('output_size', outputSize);
    formData.append('output_quality', outputQuality.toString());
    formData.append('output_format', outputFormat);

    try {
      const response = await fetch('/merge', {
        method: 'POST',
        body: formData,
      });
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
        setResult(data.result_image);
        setMergeStats({
          matches: data.matches,
          processingTime: data.processing_time
        });
        setLastMergedAs('all');
        setLastMergedIndices(null);
      } else {
        setError(data.message || 'Merge failed.');
        setMergeStats(null);
      }
    } catch (err: any) {
      setError('Error during merge: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    if (!files || files.length < 2) return;
    setScanLoading(true);
    setError(null);
    setScanResult(null);
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('images', file as Blob);
    });
    formData.append('threshold', threshold.toString());
    formData.append('use_orb', useOrb.toString());
    formData.append('min_matches', minMatches.toString());
    try {
      const response = await fetch('/scan', { method: 'POST', body: formData });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      const data = await response.json();
      if (data.success) {
        setScanResult({
          pairs: data.pairs || [],
          groups: data.groups || [],
          image_names: data.image_names || []
        });
        setPreviewUrls({});
      } else {
        setError(data.message || 'Scan failed.');
      }
    } catch (err: any) {
      setError('Scan failed: ' + err.message);
    } finally {
      setScanLoading(false);
    }
  };

  const handleMergeIndices = async (indices: number[], download: boolean) => {
    if (!files || indices.length < 2 || indices.some(idx => idx < 0 || idx >= files.length)) return;
    setMergeIndicesLoading(indices);
    setError(null);
    const formData = new FormData();
    indices.forEach(idx => formData.append('images', files[idx] as Blob));
    formData.append('blend_mode', blendMode);
    formData.append('threshold', threshold.toString());
    formData.append('use_orb', useOrb.toString());
    formData.append('alpha', alpha.toString());
    formData.append('ransac_threshold', ransacThreshold.toString());
    formData.append('feature_count', featureCount.toString());
    formData.append('match_ratio', matchRatio.toString());
    formData.append('min_matches', minMatches.toString());
    formData.append('auto_crop', autoCrop.toString());
    formData.append('output_size', outputSize);
    formData.append('output_quality', outputQuality.toString());
    formData.append('output_format', outputFormat);
    try {
      const response = await fetch('/merge', { method: 'POST', body: formData });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      const data = await response.json();
      if (data.success && data.result_image) {
        setResult(data.result_image);
        setMergeStats({
          matches: data.matches,
          processingTime: data.processing_time
        });
        setLastMergedAs('indices');
        setLastMergedIndices(indices);
        if (download) {
          const a = document.createElement('a');
          a.href = data.result_image;
          a.download = `merged-${indices.map(i => i + 1).join('-')}.${outputFormat}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      } else {
        setError(data.message || 'Merge failed.');
      }
    } catch (err: any) {
      setError(download ? 'Merge & download failed: ' + err.message : 'Merge failed: ' + err.message);
    } finally {
      setMergeIndicesLoading(null);
    }
  };

  const handleMergePair = (i: number, j: number, download: boolean) => {
    handleMergeIndices([i, j], download);
  };

  const previewKey = (indices: number[]) => indices.join(',');

  const loadPreview = async (indices: number[]): Promise<string | null> => {
    if (!files || indices.length < 2 || indices.some(idx => idx < 0 || idx >= files.length)) return null;
    const formData = new FormData();
    indices.forEach(idx => formData.append('images', files[idx] as Blob));
    formData.append('blend_mode', blendMode);
    formData.append('threshold', threshold.toString());
    formData.append('use_orb', useOrb.toString());
    formData.append('alpha', alpha.toString());
    formData.append('ransac_threshold', ransacThreshold.toString());
    formData.append('feature_count', featureCount.toString());
    formData.append('match_ratio', matchRatio.toString());
    formData.append('min_matches', minMatches.toString());
    formData.append('auto_crop', autoCrop.toString());
    formData.append('output_size', outputSize);
    formData.append('output_quality', outputQuality.toString());
    formData.append('output_format', outputFormat);
    const response = await fetch('/merge', { method: 'POST', body: formData });
    if (!response.ok) return null;
    const data = await response.json();
    if (data.success && data.result_image) {
      setPreviewUrls(prev => ({ ...prev, [previewKey(indices)]: data.result_image }));
      return data.result_image;
    }
    return null;
  };

  const handlePreviewAll = async () => {
    if (!scanResult || previewAllLoading || !files) return;
    const allIndices: number[][] = [
      ...(scanResult.groups ?? []).map(g => g.indices),
      ...scanResult.pairs.map(p => [...p.indices])
    ];
    if (allIndices.length === 0) return;
    setPreviewAllLoading(true);
    setError(null);
    for (const indices of allIndices) {
      setCurrentPreviewIndices(indices);
      await loadPreview(indices);
    }
    setCurrentPreviewIndices(null);
    setPreviewAllLoading(false);
  };

  const loadingFor = (indices: number[]) =>
    (mergeIndicesLoading != null &&
      mergeIndicesLoading.length === indices.length &&
      mergeIndicesLoading.every((v, idx) => v === indices[idx])) ||
    (previewAllLoading &&
      currentPreviewIndices != null &&
      currentPreviewIndices.length === indices.length &&
      currentPreviewIndices.every((v, idx) => v === indices[idx]));

  const canRemerge =
    result != null &&
    ((lastMergedAs === 'all' && files && files.length >= 2) ||
      (lastMergedAs === 'indices' &&
        lastMergedIndices &&
        lastMergedIndices.length >= 2 &&
        files &&
        lastMergedIndices.every(idx => idx < files.length)));

  const handleRemerge = async () => {
    if (!canRemerge || loading) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('blend_mode', blendMode);
    formData.append('threshold', threshold.toString());
    formData.append('use_orb', useOrb.toString());
    formData.append('alpha', alpha.toString());
    formData.append('ransac_threshold', ransacThreshold.toString());
    formData.append('feature_count', featureCount.toString());
    formData.append('match_ratio', matchRatio.toString());
    formData.append('min_matches', minMatches.toString());
    formData.append('auto_crop', autoCrop.toString());
    formData.append('output_size', outputSize);
    formData.append('output_quality', outputQuality.toString());
    formData.append('output_format', outputFormat);
    if (lastMergedAs === 'all' && files) {
      Array.from(files).forEach(file => {
        formData.append('images', file as Blob);
      });
    } else if (lastMergedAs === 'indices' && lastMergedIndices && files) {
      lastMergedIndices.forEach(idx => formData.append('images', files[idx] as Blob));
    } else {
      setLoading(false);
      return;
    }
    try {
      const response = await fetch('/merge', { method: 'POST', body: formData });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      const data = await response.json();
      if (data.success) {
        setResult(data.result_image);
        setMergeStats({
          matches: data.matches,
          processingTime: data.processing_time
        });
      } else {
        setError(data.message || 'Re-merge failed.');
      }
    } catch (err: any) {
      setError('Re-merge failed: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (files && files.length > 1) {
      setMultiManualPoints(Array.from({ length: files.length - 1 }, () => ({ img1: [], img2: [] })));
      setManualPairIdx(0);
    }
  }, [files, showManualModal]);

  const handleMultiImageClick = (e: React.MouseEvent<HTMLImageElement>, img: 'img1' | 'img2') => {
    const rect = (e.target as HTMLImageElement).getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * (e.target as HTMLImageElement).naturalWidth;
    const y = ((e.clientY - rect.top) / rect.height) * (e.target as HTMLImageElement).naturalHeight;
    setMultiManualPoints(pointsArr => {
      const updated = [...pointsArr];
      const pair = { ...updated[manualPairIdx] };
      pair[img] = [...pair[img], [x, y]];
      updated[manualPairIdx] = pair;
      return updated;
    });
    if (img === 'img1') {
      setManualStep('img2');
    } else {
      setManualStep('img1');
      // Only increment if there are more pairs to process
      if (files && manualPairIdx < files.length - 2) {
        setManualPairIdx(idx => idx + 1);
      }
    }
  };

  const handleMultiRemovePoint = (img: 'img1' | 'img2', idx: number) => {
    setMultiManualPoints(pointsArr => {
      const updated = [...pointsArr];
      const pair = { ...updated[manualPairIdx] };
      pair[img] = [...pair[img].slice(0, idx), ...pair[img].slice(idx + 1)];
      updated[manualPairIdx] = pair;
      return updated;
    });
  };

  const handleMultiResetPoints = () => {
    setMultiManualPoints(pointsArr => {
      const updated = [...pointsArr];
      updated[manualPairIdx] = { img1: [], img2: [] };
      return updated;
    });
    setManualStep('img1');
    setManualPairIdx(0);
  };

  const canSubmitAllPairs = multiManualPoints.length > 0 && multiManualPoints.every(pair => pair.img1.length >= 4 && pair.img2.length >= 4);

  const handleMultiManualSubmit = async () => {
    if (!files || files.length < 2) return;
    setLoading(true);
    setError(null);
    setShowManualModal(false);
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('images', file as Blob);
    });
    const matches = multiManualPoints.map(pair => pair.img1.map((pt, i) => [pt, pair.img2[i]]));
    formData.append('multi_manual_matches', JSON.stringify(matches));
    try {
      const response = await fetch('/manual_match', {
        method: 'POST',
        body: formData,
      });
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
        setResult(data.result_image);
      } else {
        setError(data.message || 'Manual merge failed.');
      }
    } catch (err: any) {
      setError('Error during manual merge: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!feedbackText.trim()) {
      setError('Please provide feedback before submitting.');
      return;
    }

    setAdjustingConfig(true);
    setError(null);

    // Collect current merge config
    const currentConfig = {
      threshold,
      alpha,
      blend_mode: blendMode,
      use_orb: useOrb,
      ransac_threshold: ransacThreshold,
      feature_count: featureCount,
      match_ratio: matchRatio,
      min_matches: minMatches,
      auto_crop: autoCrop,
      output_size: outputSize,
      output_quality: outputQuality,
      output_format: outputFormat
    };

    try {
      const response = await fetch('/adjust_config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          feedback: feedbackText,
          merge_config: currentConfig,
          result_image: result ?? undefined
        })
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }

      const data = await response.json();
      
      if (data.success && data.adjusted_config) {
        const adjusted = data.adjusted_config;
        
        // Compare old and new config to identify changes
        const changes = identifyChanges(currentConfig, adjusted);
        
        if (changes.length > 0) {
          // Store adjusted config and changes for the changes modal
          setPendingAdjustedConfig(adjusted);
          setConfigChanges(changes);
          // Show changes modal instead of directly applying
          setShowChangesModal(true);
        } else {
          // No changes detected, just close the feedback modal
          setShowFeedbackModal(false);
          setFeedbackText('');
          setError(null);
          alert('AI analyzed your feedback but no configuration changes were needed.');
        }
      } else {
        throw new Error(data.message || 'Failed to adjust configuration');
      }
    } catch (err: any) {
      setError('Error adjusting configuration: ' + err.message);
    } finally {
      setAdjustingConfig(false);
    }
  };

  const handleFeedbackModalOpen = () => {
    setFeedbackText('');
    setError(null);
    setShowFeedbackModal(true);
  };

  const handleFeedbackModalClose = () => {
    setShowFeedbackModal(false);
    setFeedbackText('');
    setError(null);
  };

  // Helper function to format config values for display
  const formatConfigValue = (key: string, value: any): string => {
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    if (key === 'blend_mode') {
      const modeLabels: { [key: string]: string } = {
        'feature_aligned': 'Feature-Aligned Blend',
        'multi_band': 'Multi-Band Blending',
        'gradient_domain': 'Gradient Domain Blending',
        'simple_overlay': 'Simple Overlay',
        'panorama': 'Panorama Stitching'
      };
      return modeLabels[value] || value;
    }
    if (key === 'output_size') {
      const sizeLabels: { [key: string]: string } = {
        'original': 'Original Size',
        'fit_screen': 'Fit to Screen',
        'custom': 'Custom'
      };
      return sizeLabels[value] || value;
    }
    if (key === 'output_format') {
      return value.toUpperCase();
    }
    return String(value);
  };

  // Helper function to get human-readable labels for config keys
  const getConfigLabel = (key: string): string => {
    const labels: { [key: string]: string } = {
      'threshold': 'Feature Match Threshold',
      'alpha': 'Blend Alpha',
      'blend_mode': 'Blending Algorithm',
      'use_orb': 'Use ORB Detector',
      'ransac_threshold': 'RANSAC Threshold',
      'feature_count': 'Feature Count',
      'match_ratio': 'Match Ratio (Lowe\'s Test)',
      'min_matches': 'Minimum Matches Required',
      'auto_crop': 'Auto Crop Black Borders',
      'output_size': 'Output Size',
      'output_quality': 'Output Quality',
      'output_format': 'Output Format'
    };
    return labels[key] || key;
  };

  // Function to compare configs and identify changes
  const identifyChanges = (oldConfig: any, newConfig: any): Array<{
    key: string;
    label: string;
    oldValue: any;
    newValue: any;
  }> => {
    const changes: Array<{
      key: string;
      label: string;
      oldValue: any;
      newValue: any;
    }> = [];

    const keys = Object.keys(oldConfig);
    keys.forEach(key => {
      if (oldConfig[key] !== newConfig[key]) {
        changes.push({
          key,
          label: getConfigLabel(key),
          oldValue: oldConfig[key],
          newValue: newConfig[key]
        });
      }
    });

    return changes;
  };

  // Function to apply the adjusted config after user confirms
  const applyAdjustedConfig = (adjusted: any) => {
    if (adjusted.threshold !== undefined) setThreshold(adjusted.threshold);
    if (adjusted.alpha !== undefined) setAlpha(adjusted.alpha);
    if (adjusted.blend_mode !== undefined) setBlendMode(adjusted.blend_mode);
    if (adjusted.use_orb !== undefined) setUseOrb(adjusted.use_orb);
    if (adjusted.ransac_threshold !== undefined) setRansacThreshold(adjusted.ransac_threshold);
    if (adjusted.feature_count !== undefined) setFeatureCount(adjusted.feature_count);
    if (adjusted.match_ratio !== undefined) setMatchRatio(adjusted.match_ratio);
    if (adjusted.min_matches !== undefined) setMinMatches(adjusted.min_matches);
    if (adjusted.auto_crop !== undefined) setAutoCrop(adjusted.auto_crop);
    if (adjusted.output_size !== undefined) setOutputSize(adjusted.output_size);
    if (adjusted.output_quality !== undefined) setOutputQuality(adjusted.output_quality);
    if (adjusted.output_format !== undefined) setOutputFormat(adjusted.output_format);
  };

  const handleChangesModalConfirm = () => {
    if (pendingAdjustedConfig) {
      applyAdjustedConfig(pendingAdjustedConfig);
      setShowChangesModal(false);
      setShowFeedbackModal(false);
      setFeedbackText('');
      setPendingAdjustedConfig(null);
      setConfigChanges([]);
      setError(null);
    }
  };

  const handleChangesModalCancel = () => {
    setShowChangesModal(false);
    setPendingAdjustedConfig(null);
    setConfigChanges([]);
    // Keep feedback modal open so user can try again
  };

  return (
    <div className="container">
      <div className="row mt-4">
        <div className="col-lg-6 mb-4">
          <div className="card shadow-sm mb-4">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">Upload Images</h5>
            </div>
            <div className="card-body">
              <div className="mb-3">
                <label htmlFor="fileInput" className="form-label fw-bold">Select images to merge</label>
                <div className="input-group">
                  <input
                    id="fileInput"
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    className="form-control"
                    accept="image/*"
                    aria-describedby="fileHelp"
                  />
                  <button
                    className="btn btn-outline-secondary"
                    type="button"
                    onClick={() => document.getElementById('fileInput')?.click()}
                  >
                    Browse
                  </button>
                </div>
                <div id="fileHelp" className="form-text">
                  Supported formats: JPG, PNG, BMP, SVG. Maximum file size: 16MB
                </div>
              </div>
              {selectedImagePreviews.length > 0 && (
                <div className="selected-images-strip mt-3">
                  <div className="d-flex gap-2 overflow-auto pb-2 flex-nowrap" style={{ minHeight: 56 }}>
                    {selectedImagePreviews.map((p, idx) => (
                      <div key={idx} className="selected-images-strip-item flex-shrink-0 text-center" title={p.name}>
                        <img
                          src={p.url}
                          alt=""
                          className="rounded border"
                          style={{ width: 48, height: 48, objectFit: 'cover' }}
                        />
                        <div className="small text-muted mt-1" style={{ fontSize: 0.7 + 'rem' }}>{p.index}. {p.shortName}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          {files && files.length >= 2 && (
            <div className="card shadow-sm mb-4">
              <div className="card-header bg-light">
                <h6 className="mb-0">Step 2: Find mergeable pairs</h6>
              </div>
              <div className="card-body">
                <p className="text-muted small mb-3">
                  Analyzes your images and lists pairs or groups that can be merged.
                </p>
                <button
                  type="button"
                  onClick={handleScan}
                  disabled={scanLoading || loading}
                  className="btn btn-primary w-100"
                  aria-label="Scan for mergeable image pairs"
                >
                  {scanLoading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
                      Scanning…
                    </>
                  ) : (
                    <>
                      <i className="bi bi-search me-1"></i>Scan for matches
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
          <div className="card mb-4">
            <div className="card-header d-flex align-items-center justify-content-between">
              <div>
                <i className="bi bi-gear-fill me-2"></i>
                <span>Merge Options</span>
              </div>
            </div>
            <div className="card-body">
              {/* Preset Buttons */}
              <div className="mb-4">
                <label className="form-label fw-bold">Quick Presets</label>
                <div className="d-flex flex-wrap gap-2">
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => applyPreset('quick')}>
                    <i className="bi bi-lightning-fill me-1"></i>Quick
                  </button>
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => applyPreset('balanced')}>
                    <i className="bi bi-speedometer2 me-1"></i>Balanced
                  </button>
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => applyPreset('high_quality')}>
                    <i className="bi bi-star-fill me-1"></i>High Quality
                  </button>
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => applyPreset('night_mode')}>
                    <i className="bi bi-moon-fill me-1"></i>Night Mode
                  </button>
                </div>
              </div>

              {/* Accordion for Options */}
              <div className="accordion" id="mergeOptionsAccordion">
                {/* Basic Settings */}
                <div className="accordion-item">
                  <h2 className="accordion-header">
                    <button 
                      className={`accordion-button ${expandedSections.basicSettings ? '' : 'collapsed'}`} 
                      type="button" 
                      onClick={() => toggleSection('basicSettings')}
                    >
                      <i className="bi bi-sliders me-2"></i>Basic Settings
                    </button>
                  </h2>
                  <div id="basicSettings" className={`accordion-collapse collapse ${expandedSections.basicSettings ? 'show' : ''}`}>
                    <div className="accordion-body">
                      <div className="mb-3">
                        <label htmlFor="threshold" className="form-label d-flex justify-content-between">
                          <span>Feature Match Threshold</span>
                          <span className="badge bg-info">{threshold}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="threshold"
                          min="0"
                          max="1"
                          step="0.1"
                          value={threshold}
                          onChange={(e) => setThreshold(parseFloat(e.target.value))}
                        />
                        <small className="text-muted">Lower values find more matches but may be less accurate</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="alpha" className="form-label d-flex justify-content-between">
                          <span>Blend Alpha</span>
                          <span className="badge bg-info">{alpha}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="alpha"
                          min="0"
                          max="1"
                          step="0.1"
                          value={alpha}
                          onChange={(e) => setAlpha(parseFloat(e.target.value))}
                        />
                        <small className="text-muted">Adjust blend strength between images</small>
                      </div>
                      <div className="mb-3">
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="manualFeatures"
                            checked={manualFeatures}
                            onChange={(e) => setManualFeatures(e.target.checked)}
                          />
                          <label className="form-check-label" htmlFor="manualFeatures">
                            Manual Feature Selection
                          </label>
                        </div>
                        <small className="text-muted d-block mt-1">Select matching points manually for better control</small>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Blend Mode */}
                <div className="accordion-item">
                  <h2 className="accordion-header">
                    <button 
                      className={`accordion-button ${expandedSections.blendMode ? '' : 'collapsed'}`} 
                      type="button" 
                      onClick={() => toggleSection('blendMode')}
                    >
                      <i className="bi bi-layers me-2"></i>Blend Mode
                    </button>
                  </h2>
                  <div id="blendMode" className={`accordion-collapse collapse ${expandedSections.blendMode ? 'show' : ''}`}>
                    <div className="accordion-body">
                      <div className="mb-3">
                        <label htmlFor="blendModeSelect" className="form-label">Blending Algorithm</label>
                        <select
                          className="form-select"
                          id="blendModeSelect"
                          value={blendMode}
                          onChange={(e) => setBlendMode(e.target.value)}
                        >
                          <option value="feature_aligned">Feature-Aligned Blend (Default)</option>
                          <option value="multi_band">Multi-Band Blending</option>
                          <option value="gradient_domain">Gradient Domain Blending</option>
                          <option value="simple_overlay">Simple Overlay</option>
                          <option value="panorama">Panorama Stitching</option>
                        </select>
                        <small className="text-muted d-block mt-1">
                          {blendMode === 'feature_aligned' && 'Uses feature detection for alignment'}
                          {blendMode === 'multi_band' && 'Seamless blending with Laplacian pyramids'}
                          {blendMode === 'gradient_domain' && 'Better seam handling'}
                          {blendMode === 'simple_overlay' && 'Basic overlay without alignment'}
                          {blendMode === 'panorama' && 'Full panorama mode'}
                        </small>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Feature Detection */}
                <div className="accordion-item">
                  <h2 className="accordion-header">
                    <button 
                      className={`accordion-button ${expandedSections.featureDetection ? '' : 'collapsed'}`} 
                      type="button" 
                      onClick={() => toggleSection('featureDetection')}
                    >
                      <i className="bi bi-search me-2"></i>Feature Detection
                    </button>
                  </h2>
                  <div id="featureDetection" className={`accordion-collapse collapse ${expandedSections.featureDetection ? 'show' : ''}`}>
                    <div className="accordion-body">
                      <div className="mb-3">
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="useOrb"
                            checked={useOrb}
                            onChange={(e) => setUseOrb(e.target.checked)}
                          />
                          <label className="form-check-label" htmlFor="useOrb">
                            Use ORB Detector
                          </label>
                        </div>
                        <small className="text-muted d-block mt-1">Recommended for night/low-light images</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="featureCount" className="form-label d-flex justify-content-between">
                          <span>Feature Count</span>
                          <span className="badge bg-info">{featureCount}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="featureCount"
                          min="500"
                          max="5000"
                          step="500"
                          value={featureCount}
                          onChange={(e) => setFeatureCount(parseInt(e.target.value))}
                        />
                        <small className="text-muted">Number of features to detect (more = slower but better)</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="matchRatio" className="form-label d-flex justify-content-between">
                          <span>Match Ratio (Lowe's Test)</span>
                          <span className="badge bg-info">{matchRatio}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="matchRatio"
                          min="0.5"
                          max="0.9"
                          step="0.05"
                          value={matchRatio}
                          onChange={(e) => setMatchRatio(parseFloat(e.target.value))}
                        />
                        <small className="text-muted">Lower values = stricter matching</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="ransacThreshold" className="form-label d-flex justify-content-between">
                          <span>RANSAC Threshold</span>
                          <span className="badge bg-info">{ransacThreshold}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="ransacThreshold"
                          min="1"
                          max="10"
                          step="0.5"
                          value={ransacThreshold}
                          onChange={(e) => setRansacThreshold(parseFloat(e.target.value))}
                        />
                        <small className="text-muted">Maximum allowed reprojection error</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="minMatches" className="form-label d-flex justify-content-between">
                          <span>Minimum Matches Required</span>
                          <span className="badge bg-info">{minMatches}</span>
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="minMatches"
                          min="4"
                          max="20"
                          step="1"
                          value={minMatches}
                          onChange={(e) => setMinMatches(parseInt(e.target.value))}
                        />
                        <small className="text-muted">Minimum feature matches needed for merge</small>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Output Options */}
                <div className="accordion-item">
                  <h2 className="accordion-header">
                    <button 
                      className={`accordion-button ${expandedSections.outputOptions ? '' : 'collapsed'}`} 
                      type="button" 
                      onClick={() => toggleSection('outputOptions')}
                    >
                      <i className="bi bi-file-earmark-image me-2"></i>Output Options
                    </button>
                  </h2>
                  <div id="outputOptions" className={`accordion-collapse collapse ${expandedSections.outputOptions ? 'show' : ''}`}>
                    <div className="accordion-body">
                      <div className="mb-3">
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="autoCrop"
                            checked={autoCrop}
                            onChange={(e) => setAutoCrop(e.target.checked)}
                          />
                          <label className="form-check-label" htmlFor="autoCrop">
                            Auto Crop Black Borders
                          </label>
                        </div>
                        <small className="text-muted d-block mt-1">Remove black borders from result</small>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="outputSize" className="form-label">Output Size</label>
                        <select
                          className="form-select"
                          id="outputSize"
                          value={outputSize}
                          onChange={(e) => setOutputSize(e.target.value)}
                        >
                          <option value="original">Original Size</option>
                          <option value="fit_screen">Fit to Screen</option>
                          <option value="custom">Custom (Coming Soon)</option>
                        </select>
                      </div>
                      <div className="mb-3">
                        <label htmlFor="outputFormat" className="form-label">Output Format</label>
                        <select
                          className="form-select"
                          id="outputFormat"
                          value={outputFormat}
                          onChange={(e) => setOutputFormat(e.target.value)}
                        >
                          <option value="png">PNG (Lossless)</option>
                          <option value="jpg">JPEG (Compressed)</option>
                          <option value="webp">WebP (Modern)</option>
                        </select>
                      </div>
                      {outputFormat !== 'png' && (
                        <div className="mb-3">
                          <label htmlFor="outputQuality" className="form-label d-flex justify-content-between">
                            <span>Quality</span>
                            <span className="badge bg-info">{outputQuality}</span>
                          </label>
                          <input
                            type="range"
                            className="form-range"
                            id="outputQuality"
                            min="1"
                            max="100"
                            step="1"
                            value={outputQuality}
                            onChange={(e) => setOutputQuality(parseInt(e.target.value))}
                          />
                          <small className="text-muted">Higher = better quality, larger file size</small>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {scanResult && (
            <div className="card mb-3">
              <div className="card-header d-flex align-items-center justify-content-between flex-wrap gap-2">
                <span><i className="bi bi-link-45deg me-2"></i>Step 3: Choose what to merge</span>
                {(scanResult.pairs.length > 0 || (scanResult.groups?.length ?? 0) > 0) && (
                  <span className="badge bg-secondary">
                    {scanResult.pairs.length} pair{scanResult.pairs.length !== 1 ? 's' : ''}
                    {(scanResult.groups?.length ?? 0) > 0 && `, ${scanResult.groups!.length} group${scanResult.groups!.length !== 1 ? 's' : ''}`}
                  </span>
                )}
              </div>
              <div className="card-body">
                {scanResult.pairs.length === 0 && (scanResult.groups?.length ?? 0) === 0 ? (
                  <>
                    <p className="text-muted mb-2">No mergeable pairs or groups found. Try lowering &quot;Minimum feature matches&quot; or using ORB for low-light images.</p>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={handleScan}
                      disabled={scanLoading || loading}
                      aria-label="Scan again"
                    >
                      {scanLoading ? <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" /> : <i className="bi bi-arrow-clockwise me-1"></i>}
                      Scan again
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-muted small mb-2">
                      Click a thumbnail to set as result; use Merge to create it. Use Preview all to generate all previews at once.
                    </p>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary mb-3"
                      disabled={previewAllLoading || loading}
                      onClick={handlePreviewAll}
                      aria-label="Preview all merge combinations"
                    >
                      {previewAllLoading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                          Loading previews…
                        </>
                      ) : (
                        <>
                          <i className="bi bi-grid-3x3-gap me-1"></i>Preview all
                        </>
                      )}
                    </button>
                    {(scanResult.groups?.length ?? 0) > 0 && (
                      <>
                        <h6 className="text-muted small text-uppercase mb-2">Groups (3+ images)</h6>
                        <div className="row g-2 mb-3">
                          {(scanResult.groups ?? []).map((group, gIdx) => {
                            const indices = group.indices;
                            const key = previewKey(indices);
                            const loadingThis = loadingFor(indices);
                            const previewUrl = previewUrls[key];
                            const label = indices.length > 2
                              ? `Images ${indices.map(i => i + 1).join(', ')} (${indices.length} images)`
                              : null;
                            if (!label) return null;
                            return (
                              <div key={`g-${gIdx}-${indices.join('-')}`} className="col-12">
                                <div className="card match-card h-100">
                                  <div className="card-body py-2 px-3 d-flex align-items-center gap-3 flex-wrap">
                                    {previewUrl ? (
                                      <button
                                        type="button"
                                        className="p-0 border-0 bg-transparent rounded overflow-hidden flex-shrink-0"
                                        style={{ width: 80, height: 80 }}
                                        onClick={() => {
                                          setResult(previewUrl);
                                          setLastMergedAs('indices');
                                          setLastMergedIndices(indices);
                                        }}
                                        title="Set as main result"
                                        aria-label="Set as main result"
                                      >
                                        <img src={previewUrl} alt="" style={{ width: 80, height: 80, objectFit: 'cover' }} />
                                      </button>
                                    ) : (
                                      <div className="d-flex align-items-center justify-content-center flex-shrink-0 bg-light rounded" style={{ width: 80, height: 80 }}>
                                        {loadingThis ? (
                                          <span className="spinner-border spinner-border-sm text-secondary" role="status" aria-hidden="true" />
                                        ) : (
                                          <span className="text-muted small">—</span>
                                        )}
                                      </div>
                                    )}
                                    <span className="flex-grow-1 small">{label}</span>
                                    <div className="d-flex gap-1 flex-shrink-0">
                                      <button
                                        type="button"
                                        className="btn btn-sm btn-primary"
                                        disabled={loadingThis || loading}
                                        onClick={() => handleMergeIndices(indices, false)}
                                        aria-label="Merge this group"
                                      >
                                        {loadingThis ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> : 'Merge'}
                                      </button>
                                      <button
                                        type="button"
                                        className="btn btn-sm btn-outline-success"
                                        disabled={loadingThis || loading}
                                        onClick={() => handleMergeIndices(indices, true)}
                                        aria-label="Merge and download"
                                      >
                                        {loadingThis ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> : <><i className="bi bi-download me-1"></i>Merge &amp; download</>}
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                    {scanResult.pairs.length > 0 && (
                      <>
                        <h6 className="text-muted small text-uppercase mb-2">Pairs</h6>
                        <div className="row g-2">
                          {[...scanResult.pairs]
                            .slice()
                            .sort((a, b) => b.match_count - a.match_count)
                            .map((pair, idx) => {
                              const [i, j] = pair.indices;
                              const indices = [i, j];
                              const key = previewKey(indices);
                              const loadingThis = loadingFor(indices);
                              const previewUrl = previewUrls[key];
                              return (
                                <div key={`${i}-${j}-${pair.match_count}-${idx}`} className="col-12">
                                  <div className="card match-card h-100">
                                    <div className="card-body py-2 px-3 d-flex align-items-center gap-3 flex-wrap">
                                      {previewUrl ? (
                                        <button
                                          type="button"
                                          className="p-0 border-0 bg-transparent rounded overflow-hidden flex-shrink-0"
                                          style={{ width: 80, height: 80 }}
                                          onClick={() => {
                                            setResult(previewUrl);
                                            setLastMergedAs('indices');
                                            setLastMergedIndices(indices);
                                          }}
                                          title="Set as main result"
                                          aria-label="Set as main result"
                                        >
                                          <img src={previewUrl} alt="" style={{ width: 80, height: 80, objectFit: 'cover' }} />
                                        </button>
                                      ) : (
                                        <div className="d-flex align-items-center justify-content-center flex-shrink-0 bg-light rounded" style={{ width: 80, height: 80 }}>
                                          {loadingThis ? (
                                            <span className="spinner-border spinner-border-sm text-secondary" role="status" aria-hidden="true" />
                                          ) : (
                                            <span className="text-muted small">—</span>
                                          )}
                                        </div>
                                      )}
                                      <span className="flex-grow-1 small">
                                        Image {i + 1} ↔ Image {j + 1}: <strong>{pair.match_count}</strong> matches
                                      </span>
                                      <div className="d-flex gap-1 flex-shrink-0">
                                        <button
                                          type="button"
                                          className="btn btn-sm btn-primary"
                                          disabled={loadingThis || loading}
                                          onClick={() => handleMergePair(i, j, false)}
                                          aria-label="Merge this pair"
                                        >
                                          {loadingThis ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> : 'Merge'}
                                        </button>
                                        <button
                                          type="button"
                                          className="btn btn-sm btn-outline-success"
                                          disabled={loadingThis || loading}
                                          onClick={() => handleMergePair(i, j, true)}
                                          aria-label="Merge and download"
                                        >
                                          {loadingThis ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" /> : <><i className="bi bi-download me-1"></i>Merge &amp; download</>}
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
          <button
            onClick={handleMerge}
            disabled={loading}
            className="btn btn-primary w-100"
            title="Merge first two images, or use the result from a chosen pair/group above"
            aria-label="Merge images (uses first two if no pair chosen above)"
          >
            Merge Images
          </button>
          <p className="text-muted small mt-1 mb-0">
            Uses first two images if you haven&apos;t chosen a pair from the list above.
          </p>
          {loading && (
            <div className="loading-overlay d-flex justify-content-center align-items-center">
              <div className="spinner-border text-primary" role="status" style={{ width: 60, height: 60 }}>
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          )}
          {error && <p className="error mt-2">{error}</p>}
        </div>
        <div className="col-lg-6 mb-4">
          {result && (
            <div className="card">
              <div className="card-header">Result</div>
              <div className="card-body text-center">
                <img src={result} alt="Merged Result" className="img-fluid" />
                {mergeStats && (
                  <div className="mt-3 p-2 bg-light rounded">
                    <small className="text-muted d-block">
                      {mergeStats.matches !== undefined && `Matches: ${mergeStats.matches} | `}
                      {mergeStats.processingTime !== undefined && `Time: ${mergeStats.processingTime.toFixed(2)}s`}
                    </small>
                  </div>
                )}
                <a
                  href={result}
                  download={`merged-image.${outputFormat}`}
                  className="btn btn-success mt-3"
                  style={{ display: 'inline-block' }}
                >
                  <i className="bi bi-download me-1"></i>Save Image
                </a>
                <button
                  onClick={handleRemerge}
                  disabled={!canRemerge || loading}
                  className="btn btn-outline-primary mt-3 ms-2"
                  style={{ display: 'inline-block' }}
                  title="Merge again with current settings (e.g. after changing blend or threshold)"
                >
                  {loading ? (
                    <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                  ) : (
                    <i className="bi bi-arrow-repeat me-1"></i>
                  )}
                  Re-merge
                </button>
                <button
                  onClick={handleFeedbackModalOpen}
                  className="btn btn-primary mt-3 ms-2"
                  style={{ display: 'inline-block' }}
                >
                  <i className="bi bi-robot me-1"></i>Get AI Feedback
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      {showManualModal && files && files.length > 1 && (
        <div className="modal show d-block" tabIndex={-1} role="dialog" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Manual Feature Selection (Pair {manualPairIdx + 1} of {files.length - 1})</h5>
                <button type="button" className="btn-close" aria-label="Close" onClick={handleManualModalClose}></button>
              </div>
              <div className="modal-body">
                <div className="row">
                  {[0, 1].map((idx) => {
                    const fileIdx = manualPairIdx + idx;
                    return (
                      <div className="col-6 text-center" key={idx} style={{ position: 'relative' }}>
                        <div className="mb-2">Image {fileIdx + 1}</div>
                        {files && files[fileIdx] && (
                          <div style={{ position: 'relative', display: 'inline-block' }}>
                            <img
                              ref={idx === 0 ? img1Ref : img2Ref}
                              src={URL.createObjectURL(files[fileIdx])}
                              alt={`img${fileIdx + 1}`}
                              className="img-fluid border"
                              style={{ cursor: manualStep === `img${idx + 1}` ? 'crosshair' : 'not-allowed', maxHeight: 350 }}
                              onClick={manualStep === `img${idx + 1}` ? (e) => handleMultiImageClick(e, idx === 0 ? 'img1' : 'img2') : undefined}
                              onLoad={() => setImageLoaded(prev => !prev)}
                            />
                            {(multiManualPoints[manualPairIdx]?.[idx === 0 ? 'img1' : 'img2'] || []).map((pt, i) => {
                              const imgRef = idx === 0 ? img1Ref.current : img2Ref.current;
                              const naturalWidth = imgRef?.naturalWidth || 1;
                              const naturalHeight = imgRef?.naturalHeight || 1;
                              const displayWidth = imgRef?.clientWidth || 1;
                              const displayHeight = imgRef?.clientHeight || 1;
                              
                              // Convert natural coordinates to display coordinates
                              const scaleX = displayWidth / naturalWidth;
                              const scaleY = displayHeight / naturalHeight;
                              const displayX = pt[0] * scaleX;
                              const displayY = pt[1] * scaleY;
                              
                              return (
                                <div
                                  key={i}
                                  style={{
                                    position: 'absolute',
                                    left: `${displayX - 10}px`,
                                    top: `${displayY - 10}px`,
                                    width: 20,
                                    height: 20,
                                    background: idx === 0 ? '#0d6efd' : '#198754',
                                    borderRadius: '50%',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 'bold',
                                    fontSize: 12,
                                    border: '2px solid white',
                                    zIndex: 2,
                                    pointerEvents: 'none',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                                  }}
                                >
                                  {i + 1}
                                </div>
                              );
                            })}
                          </div>
                        )}
                        <div className="mt-2">
                          {(multiManualPoints[manualPairIdx]?.[idx === 0 ? 'img1' : 'img2'] || []).map((pt, i) => (
                            <span key={i} className={idx === 0 ? 'badge bg-primary me-1' : 'badge bg-success me-1'}>
                              ({pt[0].toFixed(0)}, {pt[1].toFixed(0)})
                              <button
                                type="button"
                                className="btn btn-sm btn-link text-danger p-0 ms-1"
                                style={{ fontSize: 12 }}
                                onClick={() => handleMultiRemovePoint(idx === 0 ? 'img1' : 'img2', i)}
                                tabIndex={-1}
                              >
                                ×
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 text-center">
                  <p>Click a point on the left image, then the corresponding point on the right image. Repeat at least 4 times for each pair.</p>
                  <p>Points selected for this pair: {multiManualPoints[manualPairIdx]?.img1.length || 0}</p>
                  <button className="btn btn-outline-warning btn-sm mt-2" onClick={handleMultiResetPoints}>
                    Reset Points for This Pair
                  </button>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleManualModalClose}>Cancel</button>
                <button type="button" className="btn btn-outline-primary me-2" onClick={() => setManualPairIdx(idx => Math.max(0, idx - 1))} disabled={manualPairIdx === 0}>Previous Pair</button>
                <button type="button" className="btn btn-outline-primary me-2" onClick={() => setManualPairIdx(idx => Math.min((files.length - 2), idx + 1))} disabled={manualPairIdx === files.length - 2}>Next Pair</button>
                <button type="button" className="btn btn-primary" onClick={handleMultiManualSubmit} disabled={!canSubmitAllPairs}>Submit Manual Match</button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showFeedbackModal && (
        <div className="modal show d-block" tabIndex={-1} role="dialog" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog" role="document">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  <i className="bi bi-robot me-2"></i>Get AI Feedback on Merge Settings
                </h5>
                <button type="button" className="btn-close" aria-label="Close" onClick={handleFeedbackModalClose}></button>
              </div>
              <div className="modal-body">
                <p className="text-muted mb-3">
                  Provide feedback about the generated image result. AI will analyze your feedback and suggest adjustments to the merge configuration.
                </p>
                <div className="mb-3">
                  <label htmlFor="feedbackTextarea" className="form-label">Your Feedback</label>
                  <textarea
                    id="feedbackTextarea"
                    className="form-control"
                    rows={5}
                    placeholder="e.g., 'The images are not aligned well', 'The blend is too transparent', 'Increase feature detection sensitivity', etc."
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    disabled={adjustingConfig}
                  />
                </div>
                {error && (
                  <div className="alert alert-danger" role="alert">
                    {error}
                  </div>
                )}
                {adjustingConfig && (
                  <div className="text-center my-3">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Adjusting configuration...</span>
                    </div>
                    <p className="mt-2 text-muted">AI is analyzing your feedback and adjusting settings...</p>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleFeedbackModalClose} disabled={adjustingConfig}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleFeedbackSubmit}
                  disabled={adjustingConfig || !feedbackText.trim()}
                >
                  {adjustingConfig ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Processing...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-send me-1"></i>Submit Feedback
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showChangesModal && configChanges.length > 0 && (
        <div className="modal show d-block" tabIndex={-1} role="dialog" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content">
              <div className="modal-header bg-primary text-white">
                <h5 className="modal-title">
                  <i className="bi bi-info-circle me-2"></i>AI Configuration Changes
                </h5>
                <button type="button" className="btn-close btn-close-white" aria-label="Close" onClick={handleChangesModalCancel}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-info" role="alert">
                  <i className="bi bi-lightbulb me-2"></i>
                  <strong>AI has suggested the following changes based on your feedback:</strong>
                </div>
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th style={{ width: '35%' }}>Parameter</th>
                        <th style={{ width: '30%' }}>Old Value</th>
                        <th style={{ width: '5%' }} className="text-center">→</th>
                        <th style={{ width: '30%' }}>New Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {configChanges.map((change, index) => (
                        <tr key={change.key} className="align-middle">
                          <td>
                            <strong>{change.label}</strong>
                          </td>
                          <td>
                            <span className="badge bg-secondary">
                              {formatConfigValue(change.key, change.oldValue)}
                            </span>
                          </td>
                          <td className="text-center">
                            <i className="bi bi-arrow-right text-primary"></i>
                          </td>
                          <td>
                            <span className="badge bg-success">
                              {formatConfigValue(change.key, change.newValue)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3">
                  <small className="text-muted">
                    <i className="bi bi-info-circle me-1"></i>
                    Review the changes above. Click "Apply Changes" to update your settings, or "Cancel" to keep your current settings.
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleChangesModalCancel}>
                  <i className="bi bi-x-circle me-1"></i>Cancel
                </button>
                <button type="button" className="btn btn-primary" onClick={handleChangesModalConfirm}>
                  <i className="bi bi-check-circle me-1"></i>Apply Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <footer className="text-center text-muted my-4" style={{ fontSize: '0.95rem' }}>
        &copy; {new Date().getFullYear()} Image Merger App | Ideated and developed by JH
      </footer>
    </div>
  );
};

export default App;
