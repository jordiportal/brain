// Runtime environment configuration injection
// Este script inyecta las variables de entorno en el index.html
// antes de que Angular arranque, permitiendo configuración dinámica
// en contenedores Docker sin necesidad de recompilar

(function(window) {
  window['env'] = window['env'] || {};

  // Valores por defecto (desarrollo)
  window['env']['apiUrl'] = 'http://localhost:8000/api/v1';
  window['env']['ollamaDefaultUrl'] = 'http://localhost:11434';

  // En producción, estos valores serán reemplazados por el script
  // docker-entrypoint.sh usando las variables de entorno del contenedor
})(this);
