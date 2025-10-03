"""
Servicio de Procesamiento de Audio para Encuesta de Adultos Mayores
Implementa filtros avanzados de audio para mejorar la transcripción
"""

import os
import uuid
import wave
import numpy as np
import ffmpeg
import logging
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AudioQuality:
    """Métricas de calidad de audio"""
    noise_level: float          # 0-100 (menor es mejor)
    clarity: float              # 0-100 (mayor es mejor)
    volume: float               # Nivel de volumen detectado
    duration: float             # Duración en segundos
    sample_rate: int            # Frecuencia de muestreo
    recommendation: str         # Sugerencia de mejora

@dataclass
class VADConfig:
    """Configuración para Voice Activity Detection"""
    threshold: float = 0.5          # Sensibilidad de detección
    min_speech_duration: int = 100  # Mínimo 100ms de voz
    max_silence_duration: int = 500 # Máximo 500ms de silencio

class AudioProcessor:
    """Procesador de audio con filtros avanzados para adultos mayores"""
    
    def __init__(self):
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)
        
    def process_audio_for_elderly(self, audio_path: str) -> Tuple[str, AudioQuality]:
        """
        Procesa audio específicamente optimizado para voz de adultos mayores
        
        Args:
            audio_path: Ruta del archivo de audio original
            
        Returns:
            Tuple[str, AudioQuality]: Ruta del audio procesado y métricas de calidad
        """
        try:
            logger.info("🎵 Iniciando procesamiento de audio para adultos mayores")
            
            # 1. Analizar calidad inicial
            initial_quality = self._analyze_audio_quality(audio_path)
            logger.info(f"📊 Calidad inicial: ruido={initial_quality.noise_level:.1f}, "
                       f"claridad={initial_quality.clarity:.1f}")
            
            # 2. Crear archivo de salida optimizado
            output_path = str(self.temp_dir / f"processed_{uuid.uuid4()}.wav")
            
            # 3. Aplicar pipeline de filtros optimizado para adultos mayores
            self._apply_elderly_optimized_filters(audio_path, output_path, initial_quality)
            
            # 4. Aplicar VAD (Voice Activity Detection)
            vad_output_path = self._apply_vad_processing(output_path)
            
            # 5. Análisis de calidad final
            final_quality = self._analyze_audio_quality(vad_output_path)
            final_quality.recommendation = self._generate_quality_recommendation(
                initial_quality, final_quality
            )
            
            logger.info(f"✅ Audio procesado: {initial_quality.duration:.1f}s → "
                       f"calidad mejorada: {final_quality.clarity:.1f}")
            
            return vad_output_path, final_quality
            
        except Exception as e:
            logger.error(f"❌ Error procesando audio: {str(e)}")
            raise
    
    def _apply_elderly_optimized_filters(self, input_path: str, output_path: str, 
                                       quality: AudioQuality) -> None:
        """Aplica filtros específicamente optimizados para voz de adultos mayores"""
        
        # Filtros adaptativos basados en la calidad inicial
        filters = []
        
        # 1. Filtro pasa-altos para eliminar ruido de baja frecuencia
        # Adultos mayores: frecuencia fundamental más baja (80-120 Hz)
        highpass_freq = 80 if quality.noise_level > 50 else 60
        filters.append(f"highpass=f={highpass_freq}")
        
        # 2. Filtro pasa-bajos para eliminar ruido de alta frecuencia
        # Adultos mayores: rango de voz hasta 8kHz máximo
        lowpass_freq = 8000 if quality.clarity > 70 else 6000
        filters.append(f"lowpass=f={lowpass_freq}")
        
        # 3. Normalización de volumen adaptativa
        if quality.volume < 0.3:
            # Volumen bajo - amplificar más
            filters.append("volume=2.5")
        elif quality.volume < 0.6:
            # Volumen medio - amplificar moderadamente
            filters.append("volume=1.8")
        else:
            # Volumen alto - normalizar suavemente
            filters.append("volume=1.2")
        
        # 4. Reducción de ruido específica para adultos mayores
        if quality.noise_level > 40:
            # Filtro de reducción de ruido agresivo
            filters.extend([
                "afftdn=nr=20:nf=-20",  # Reducción de ruido FFT
                "highshelf=g=-3:f=6000", # Atenuar frecuencias altas ruidosas
            ])
        
        # 5. Compresión dinámica para voz irregular
        # Adultos mayores pueden tener volumen inconsistente
        filters.append("acompressor=threshold=0.1:ratio=3:attack=5:release=50")
        
        # 6. Filtro de de-esser para sibilantes
        # Común en adultos mayores con prótesis dentales
        filters.append("deesser")
        
        # 7. Mejora de claridad de voz
        filters.append("aphaser=in_gain=0.4:out_gain=0.74:delay=3:decay=0.4:speed=0.5")
        
        # Construir comando FFmpeg
        filter_chain = ",".join(filters)
        
        try:
            (ffmpeg
             .input(input_path)
             .output(
                 output_path,
                 acodec='pcm_s16le',    # Formato PCM 16-bit
                 ac=1,                   # Mono
                 ar=16000,               # 16kHz (óptimo para STT)
                 af=filter_chain         # Aplicar filtros
             )
             .run(overwrite_output=True, quiet=True))
             
            logger.info(f"🔧 Filtros aplicados: {filter_chain}")
            
        except ffmpeg.Error as e:
            logger.error(f"❌ Error en FFmpeg: {e}")
            raise
    
    def _apply_vad_processing(self, audio_path: str) -> str:
        """
        Aplica Voice Activity Detection para eliminar silencios
        Implementación simplificada usando análisis de energía
        """
        try:
            output_path = str(self.temp_dir / f"vad_{uuid.uuid4()}.wav")
            
            # Filtro VAD usando silenceremove de FFmpeg
            # Optimizado para voz de adultos mayores (umbrales más sensibles)
            vad_filter = (
                "silenceremove="
                "start_periods=1:"      # Eliminar silencio inicial
                "start_duration=0.3:"   # 300ms de silencio para comenzar
                "start_threshold=-45dB:" # Umbral más sensible para voz baja
                "detection=peak:"        # Detección por picos
                "stop_periods=-1:"       # Eliminar todos los silencios
                "stop_duration=0.5:"     # 500ms de silencio para cortar
                "stop_threshold=-45dB"   # Umbral sensible
            )
            
            (ffmpeg
             .input(audio_path)
             .output(output_path, af=vad_filter)
             .run(overwrite_output=True, quiet=True))
            
            logger.info("🎙️ VAD aplicado: silencios eliminados")
            
            # Limpiar archivo temporal
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error en VAD: {e}")
            return audio_path  # Retornar original si falla
    
    def _analyze_audio_quality(self, audio_path: str) -> AudioQuality:
        """Analiza la calidad del audio y genera métricas"""
        try:
            # Obtener información básica del audio
            probe = ffmpeg.probe(audio_path)
            audio_stream = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
            
            duration = float(audio_stream.get('duration', 0))
            sample_rate = int(audio_stream.get('sample_rate', 16000))
            
            # Análisis de calidad usando FFmpeg
            # Calcular RMS (Root Mean Square) para nivel de volumen
            analysis = (ffmpeg
                       .input(audio_path)
                       .filter('volumedetect')
                       .output('pipe:', format='null')
                       .run(capture_stdout=True, capture_stderr=True))
            
            # Parsear salida de volumedetect
            output = analysis[1].decode('utf-8')
            
            # Extraer métricas
            mean_volume = 0.5  # Default
            max_volume = 0.5   # Default
            
            for line in output.split('\n'):
                if 'mean_volume:' in line:
                    try:
                        mean_volume = abs(float(line.split('mean_volume:')[1].split('dB')[0].strip()))
                        mean_volume = min(mean_volume / 60, 1.0)  # Normalizar a 0-1
                    except:
                        pass
                elif 'max_volume:' in line:
                    try:
                        max_volume = abs(float(line.split('max_volume:')[1].split('dB')[0].strip()))
                        max_volume = min(max_volume / 60, 1.0)  # Normalizar a 0-1
                    except:
                        pass
            
            # Calcular métricas estimadas
            # Nivel de ruido estimado (inverso de la calidad de señal)
            noise_level = max(0, 100 - (mean_volume * 100))
            
            # Claridad estimada basada en volumen y duración
            clarity = min(100, (mean_volume * 80) + (20 if duration > 1 else 0))
            
            return AudioQuality(
                noise_level=noise_level,
                clarity=clarity,
                volume=mean_volume,
                duration=duration,
                sample_rate=sample_rate,
                recommendation=""
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Error analizando calidad: {e}")
            # Retornar métricas por defecto
            return AudioQuality(
                noise_level=50.0,
                clarity=60.0,
                volume=0.5,
                duration=5.0,
                sample_rate=16000,
                recommendation="No se pudo analizar la calidad"
            )
    
    def _generate_quality_recommendation(self, initial: AudioQuality, 
                                       final: AudioQuality) -> str:
        """Genera recomendación basada en el análisis de calidad"""
        
        if final.clarity > 80:
            return "✅ Excelente calidad de audio para transcripción"
        elif final.clarity > 60:
            return "👍 Buena calidad de audio, transcripción confiable"
        elif final.clarity > 40:
            return "⚠️ Calidad moderada, transcripción puede tener errores menores"
        else:
            return "❌ Calidad baja, se recomienda grabar en ambiente más silencioso"
    
    def cleanup_temp_files(self) -> None:
        """Limpia archivos temporales"""
        try:
            for file_path in self.temp_dir.glob("*.wav"):
                if file_path.exists():
                    file_path.unlink()
            logger.info("🧹 Archivos temporales limpiados")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando archivos temporales: {e}")
    
    def detect_audio_context(self, audio_path: str) -> str:
        """
        Detecta el contexto del audio para aplicar filtros específicos
        """
        try:
            # Análisis básico de contexto usando duración y nivel de energía
            quality = self._analyze_audio_quality(audio_path)
            
            if quality.duration < 3:
                return "conversacion_casual"  # Respuesta corta
            elif quality.noise_level > 70:
                return "ambiente_ruidoso"     # Mucho ruido de fondo
            elif quality.volume < 0.3:
                return "volumen_bajo"         # Voz muy baja
            else:
                return "conversacion_formal"  # Condiciones normales
                
        except Exception:
            return "conversacion_formal"      # Default seguro

# Instancia global del procesador
audio_processor = AudioProcessor()

def process_elderly_audio(audio_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Función principal para procesar audio de adultos mayores
    
    Args:
        audio_path: Ruta del archivo de audio original
        
    Returns:
        Tuple[str, Dict]: Ruta del audio procesado y métricas de calidad
    """
    try:
        processed_path, quality = audio_processor.process_audio_for_elderly(audio_path)
        
        quality_dict = {
            "noise_level": quality.noise_level,
            "clarity": quality.clarity,
            "volume": quality.volume,
            "duration": quality.duration,
            "sample_rate": quality.sample_rate,
            "recommendation": quality.recommendation
        }
        
        return processed_path, quality_dict
        
    except Exception as e:
        logger.error(f"❌ Error en process_elderly_audio: {e}")
        raise

def cleanup_audio_files():
    """Función de utilidad para limpiar archivos temporales"""
    audio_processor.cleanup_temp_files()