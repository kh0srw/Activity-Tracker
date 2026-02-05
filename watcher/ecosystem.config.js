module.exports = {
  apps: [
    {
      name: "activity-watcher",
      script: "watcher.py",
      // Path to the pythonw.exe inside your virtual environment
      // Using 'pythonw' hides the console window
      interpreter: "./.venv/Scripts/pythonw.exe",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      },
      // Ensures logs are saved to files instead of trying to print to a non-existent console
      error_file: "./logs/pm2_error.log",
      out_file: "./logs/pm2_out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    }
  ]
};