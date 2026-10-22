# Consulta de datos vigentes del portal

Al abrir el portal, datos-vigentes.js consulta la revisión actual de main y
carga desde esa misma revisión las dos cuentas CSV, el JSON del PIB y las seis
partes de la aplicación. Las gráficas, los indicadores y las descargas quedan
vinculados a la revisión consultada, que se muestra en «Fuente de esta
visualización». «Datos consultados» indica la fecha de la consulta.

Los cambios publicados en los CSV se reflejan al volver a abrir o actualizar
la página. No es necesario reconstruir la copia de datos incluida en el
paquete original. El año seleccionado inicialmente es el más reciente de
las cuentas.

La carga valida encabezados, identificadores, valores numéricos y cobertura
temporal. Los gases sin cuantificar permanecen vacíos. El PIB debe cubrir
los años de las cuentas. Si las fuentes no pueden consultarse o validarse,
el portal ofrece reintentar y no presenta la copia antigua como vigente.

Las fuentes se consultan por HTTPS en la API pública y en los archivos
públicos de GitHub; no se usan credenciales. La carga depende de su
disponibilidad y de los límites de consulta de GitHub.

La integración conserva el paquete visual existente. Si se sustituye ese
paquete, hay que revisar los puntos de integración de hydrate y ejecutar:

~~~bash
node --test tests/portal-datos-vigentes.test.cjs
~~~
