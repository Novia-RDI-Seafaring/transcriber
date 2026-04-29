export interface SegmentDTO {
  index: number;
  start: number;
  end: number;
  text: string;
  speaker: string;
  x: number;
  y: number;
  clip_url: string;
}

export interface ResultDTO {
  audio_name: string;
  audio_url: string | null;
  duration: number;
  n_speakers: number;
  speakers: string[];
  segments: SegmentDTO[];
}

export interface LabelsState {
  speakers: string[];
}

export interface LabelsUpdate {
  mapping: Record<string, string>;
  per_index: Record<number, string>;
}
