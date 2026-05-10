import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time

# Usa rutas absolutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
LOG_FILE = os.path.join(BASE_DIR, "service_log.txt")

class FastAPIWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'FastAPIService'
    _svc_display_name_ = 'Mi Servicio FastAPI'
    _svc_description_ = 'Servicio de Windows que expone métodos de FastAPI'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server = None

    def log(self, msg):
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.ctime()}: {msg}\n")

    def SvcStop(self):
        self.log("Recibida señal de parada...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.server:
            self.server.should_exit = True

    def SvcDoRun(self):
        self.log("Iniciando el servicio...")
        try:
            self.main()
        except Exception as e:
            self.log(f"Error en SvcDoRun: {e}")

    def main(self):
        self.log(f"Cargando uvicorn internamente...")
        os.chdir(BASE_DIR)
        
        # Importamos uvicorn aquí para asegurar que los paths estén cargados
        import uvicorn
        
        # Deshabilitar los logs por defecto para evitar problemas con formatters nativos y colorama
        config = uvicorn.Config(
            "main:app", 
            host="0.0.0.0", 
            port=8005, 
            log_config=None, # <- Quitamos la configuración ruidosa de logs por defecto
            access_log=False # <- Desactivamos el access log para evitar console-printing issues
        )
        self.server = uvicorn.Server(config)
        
        # Evitar que uvicorn choque con las señales del servicio de Windows
        self.server.install_signal_handlers = lambda: None
        
        self.log("Servidor ejecutándose...")
        self.server.run()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FastAPIWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FastAPIWindowsService)