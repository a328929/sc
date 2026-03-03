import { FolderOpen, Upload } from 'lucide-react';
import { type ChangeEvent, useRef } from 'react';

interface FilePickerSectionProps {
  onAddFiles: (files: File[]) => void;
}

export function FilePickerSection({ onAddFiles }: FilePickerSectionProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const pickedFiles = Array.from(event.target.files ?? []);
    if (pickedFiles.length > 0) {
      onAddFiles(pickedFiles);
      event.target.value = '';
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>1. 选择上传文件</h2>
        <p>支持批量多选文件；目录选择取决于安卓浏览器能力。</p>
      </div>

      <div className="picker-actions">
        <button className="btn primary" onClick={() => fileInputRef.current?.click()} type="button">
          <Upload size={18} />
          批量选择文件
        </button>

        <label className="btn ghost" htmlFor="folder-picker">
          <FolderOpen size={18} />
          尝试选择文件夹
        </label>
      </div>

      <input className="hidden-input" multiple onChange={handleInputChange} ref={fileInputRef} type="file" />
      <input
        className="hidden-input"
        id="folder-picker"
        multiple
        onChange={handleInputChange}
        type="file"
        // @ts-expect-error - webkitdirectory is non-standard but needed for directory picking.
        webkitdirectory=""
      />
    </section>
  );
}
