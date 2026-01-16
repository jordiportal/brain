export default ({ env }) => ({
  connection: {
    client: 'postgres',
    connection: {
      host: env('DATABASE_HOST', 'localhost'),
      port: env.int('DATABASE_PORT', 5432),
      database: env('DATABASE_NAME', 'brain_db'),
      user: env('DATABASE_USERNAME', 'brain'),
      password: env('DATABASE_PASSWORD', 'brain_secret'),
      ssl: env.bool('DATABASE_SSL', false),
    },
    debug: false,
  },
});
