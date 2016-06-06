class PIDController(object):
    ek_1 = 0.0  # e[k-1] = SP[k-1] - PV[k-1] = Tset_hlt[k-1] - Thlt[k-1]
    ek_2 = 0.0  # e[k-2] = SP[k-2] - PV[k-2] = Tset_hlt[k-2] - Thlt[k-2]
    xk_1 = 0.0  # PV[k-1] = Thlt[k-1]
    xk_2 = 0.0  # PV[k-2] = Thlt[k-1]
    yk_1 = 0.0  # y[k-1] = Gamma[k-1]
    yk_2 = 0.0  # y[k-2] = Gamma[k-1]

    yk = 0.0  # output

    GMA_HLIM = 100.0
    GMA_LLIM = 0.0

    def __init__(self, ts, kc, ti, td):
        self.kc = kc
        self.ti = ti
        self.td = td
        self.ts = ts
        self.k0 = 0.0
        self.k1 = 0.0
        self.k2 = 0.0
        self.k3 = 0.0
        self.ts_ticks = 0
        self.pid_model = 3
        self.pp = 0.0
        self.pi = 0.0
        self.pd = 0.0
        if self.ti == 0.0:
            self.k0 = 0.0
        else:
            self.k0 = self.kc * self.ts / self.ti
        self.k1 = self.kc * self.td / self.ts

    def calcPID(self, xk, tset, enable):
        ek = 0.0
        ek = tset - xk  # calculate e[k] = SP[k] - PV[k]

        if enable:
            # -----------------------------------------------------------
            # Calculate PID controller:
            # y[k] = y[k-1] + kc*(PV[k-1] - PV[k] +
            # Ts*e[k]/Ti +
            # Td/Ts*(2*PV[k-1] - PV[k] - PV[k-2]))
            # -----------------------------------------------------------
            self.pp = self.kc * (PIDController.xk_1 - xk)
            self.pi = self.k0 * ek
            self.pd = self.k1 * (2.0 * PIDController.xk_1 - xk -
                PIDController.xk_2)
            PIDController.yk += self.pp + self.pi + self.pd
        else:
            PIDController.yk = 0.0
            self.pp = 0.0
            self.pi = 0.0
            self.pd = 0.0
        PIDController.xk_2 = PIDController.xk_1
        PIDController.xk_1 = xk
        # limit y[k] to GMA_HLIM and GMA_LLIM
        if PIDController.yk > PIDController.GMA_HLIM:
            PIDController.yk = PIDController.GMA_HLIM
        if PIDController.yk < PIDController.GMA_LLIM:
            PIDController.yk = PIDController.GMA_LLIM
        return PIDController.yk
