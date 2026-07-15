# Diseño de la interfaz oscura y animada

Fecha: 15 de julio de 2026

Estado: aprobado mediante la maqueta visual de `docs/design/recorder-ui-concept.png`.

## Objetivo

Convertir Conference Recorder en una herramienta que RRHH pueda abrir y usar sin formación: debe explicar qué va a grabarse, mostrar si Chrome está preparado, permitir incluir o no el micrófono y guardar el MP4 donde el usuario decida. La interfaz debe transmitir calidad de producto mediante profundidad y movimiento, sin añadir pasos ni distraer durante una grabación.

Todo el texto visible, los diálogos, la página auxiliar de Chrome, los mensajes de error y la documentación de uso se presentan en castellano.

## Dirección seleccionada

Se mantiene la aplicación nativa en Tkinter y su distribución portable `onedir`. Los elementos expresivos se dibujan con `Canvas`, evitando incorporar Electron, WebView2 o un framework de UI adicional.

Alternativas descartadas:

- Una interfaz clara corporativa: legible, pero no responde a la dirección visual aprobada.
- Migrar toda la aplicación a una interfaz web embebida: facilitaría CSS, pero aumentaría mucho el tamaño, el arranque y el mantenimiento del portable.
- Añadir una introducción animada: aporta espectáculo, pero retrasa una tarea operativa. La personalidad se concentra en animaciones ambientales y transiciones inmediatas.

## Sistema visual

- Fondo principal: grafito casi negro `#0B0C10`.
- Superficies elevadas: `#151720` y `#1B1E29`.
- Texto principal: `#F7F7FA`; texto secundario: `#9CA3B5`.
- Acción y grabación: coral `#FF5A5F`.
- Profundidad y selección: violeta eléctrico `#8B5CF6`.
- Estado correcto: verde `#55E6A5`; advertencia: ámbar `#F6B94A`.
- Tipografía: Segoe UI / Segoe UI Semibold, con números monoespaciados durante la grabación.
- Geometría: radios amplios, bordes finos y aire generoso. El brillo se reserva para la selección, la grabación y la acción principal.

La maqueta es una referencia de intención, no una imagen que se incrusta en la aplicación. Iconos, órbitas, tarjetas y controles se renderizan de forma nativa y adaptativa.

## Estructura de la pantalla

1. Barra superior con identidad de producto y estado de Chrome.
2. Hero central con el estado actual y un orbe de grabación.
3. Tres tarjetas de fuente, visibles simultáneamente:
   - `Pantalla completa`.
   - `Elegir pantalla`.
   - `Pestaña de Chrome`.
4. Panel compacto de sonido:
   - activación opcional de micrófono;
   - dispositivo seleccionado cuando se activa;
   - explicación contextual del audio que se capturará.
5. Calidad de vídeo y carpeta de destino, con acción `Cambiar`.
6. Botón principal ancho, cuyo texto y color reflejan el estado.
7. Durante la grabación, cronómetro visible y acción inequívoca `Finalizar y guardar`.

## Movimiento

| Elemento | Estado | Animación |
|---|---|---|
| Orbe | En espera | Dos órbitas lentas, puntos en movimiento y respiración muy suave. |
| Orbe | Grabando | Pulso coral más marcado, sin flashes. |
| Tarjeta | Hover/foco | Elevación cromática y transición corta del borde. |
| Tarjeta | Seleccionada | Resalte coral-violeta y marca de selección. |
| Forma de onda | Micrófono activo | Onda ambiental de baja amplitud; no pretende medir audio real. |
| Acción principal | En espera | Respiración mínima del borde, sin cambiar la legibilidad. |
| Acción principal | Pulsación | Compresión visual y recuperación rápida. |

Las animaciones usan el bucle `after` de Tkinter, se detienen al destruir la ventana y no bloquean los workers de captura. La página auxiliar de Chrome replica el lenguaje con CSS y respeta `prefers-reduced-motion`.

## Comportamiento por fuente

- `Pantalla completa` comienza directamente y captura el audio del árbol de Chrome.
- `Elegir pantalla` abre el selector nativo de Chrome y exige un monitor completo.
- `Pestaña de Chrome` abre el selector nativo y exige compartir también el audio.
- El micrófono está desactivado por defecto y solo se enumera cuando se activa.
- La acción principal y el texto explicativo cambian con la fuente elegida.
- Los controles se bloquean mientras se prepara o finaliza una sesión.

## Estados y errores

- Chrome preparado, no abierto o no comprobable.
- Sin micrófonos, buscando dispositivos o dispositivo preparado.
- Preparando selector/captura, grabando, finalizando y guardado.
- Cancelación del selector y fuente incorrecta con opción de repetir.
- Errores de inicio/finalización en castellano, conservando los temporales cuando corresponde.

Los errores técnicos se muestran en texto claro. No se ocultan los detalles necesarios para que soporte pueda diagnosticar el fallo.

## Accesibilidad y ergonomía

- Contraste AA en texto y controles.
- Navegación por teclado en tarjetas, con foco visible y activación mediante `Espacio` o `Intro`.
- Áreas de clic amplias y sin controles basados únicamente en color.
- La selección siempre se comunica con borde, marca y texto contextual.
- La ventana abre centrada y cabe en el entorno objetivo de 1920×1080; mantiene una jerarquía válida al redimensionarse dentro de sus límites.
- Los mensajes de estado usan texto además de color.

## Distribución

RRHH recibe un único ZIP. Debe descomprimirlo completo y conservar juntos `Conference Recorder.exe`, `_runtime` y `tools`. No necesita Python, FFmpeg, permisos administrativos ni extensiones. Chrome debe estar abierto y Windows puede mostrar SmartScreen porque el ejecutable no tiene firma comercial.

## Criterios de aceptación

- Toda la experiencia visible está en castellano.
- La interfaz real mantiene la composición, paleta y jerarquía de la maqueta aprobada.
- Las animaciones son fluidas, no bloquean y reflejan correctamente el estado.
- Las tres fuentes y el micrófono opcional siguen funcionando como en la versión 2.1.0.
- La carpeta de salida puede cambiarse antes de grabar.
- La página auxiliar de Chrome comparte el mismo sistema visual.
- Las pruebas unitarias, lint, compilación, autodiagnóstico y build portable son correctos.
- La UI real se inspecciona visualmente en estado inicial y durante una simulación de interacción.

