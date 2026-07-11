"""
Alakoro FiberSense - Signal Uploader
Componente de upload de arquivos de sinal.
"""
import React, { useState, useRef } from 'react';
import { SignalType } from '../types';

interface SignalUploaderProps {
  signalType: SignalType;
  onUpload: (file: File) => void;
}

const SignalUploader: React.FC<SignalUploaderProps> = ({ signalType, onUpload }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptedFormats = {
    das: '.h5,.hdf5,.npy,.csv,.segy',
    dts: '.h5,.hdf5,.npy,.csv,.tdms',
    dss: '.h5,.hdf5,.npy,.csv',
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setFileName(file.name);
      onUpload(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      onUpload(file);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`p-6 border-2 border-dashed rounded-lg cursor-pointer transition-colors text-center ${
        isDragging
          ? 'border-primary-500 bg-primary-500/10'
          : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={acceptedFormats[signalType]}
        onChange={handleFileSelect}
        className="hidden"
      />

      <div className="text-4xl mb-2">📁</div>

      {fileName ? (
        <div>
          <p className="text-sm text-primary-400 font-medium">{fileName}</p>
          <p className="text-xs text-gray-500 mt-1">Clique para trocar</p>
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-300">
            Arraste um arquivo ou clique para selecionar
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Formatos: {acceptedFormats[signalType]}
          </p>
        </div>
      )}
    </div>
  );
};

export default SignalUploader;
