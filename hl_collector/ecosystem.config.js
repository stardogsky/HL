module.exports = {
  apps: [
    {
      name: "hl_collector",
      script: "main.py",
      interpreter: "python3",
      cwd: "/home/moltbot/HL/hl_collector",
      env: {
        PYTHONUNBUFFERED: "1",
      },
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 50,
      out_file: "/home/moltbot/HL/logs/hl_collector-out.log",
      error_file: "/home/moltbot/HL/logs/hl_collector-err.log",
      time: true,
    },
  ],
};
