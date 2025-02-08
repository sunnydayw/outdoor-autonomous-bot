class MovingAverageFilter:
    # A simple approach is to average the last N measurements. It’s easy to implement and effective for reducing random noise, though it introduces a delay.
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.values = []
    
    def update(self, measurement):
        self.values.append(measurement)
        if len(self.values) > self.window_size:
            self.values.pop(0)
        return sum(self.values) / len(self.values)

class ExponentialMovingAverage:
    # This filter gives more weight to recent measurements and is computationally lightweight.
    def __init__(self, alpha=0.2, initial_value=0):
        self.alpha = alpha
        self.x = initial_value
    
    def update(self, measurement):
        self.x = self.alpha * measurement + (1 - self.alpha) * self.x
        return self.x

class KalmanFilter:
    def __init__(self, Q=0.01, R=0.1, initial_value=0):
        # Q: Process noise covariance
        # R: Measurement noise covariance
        self.Q = Q
        self.R = R
        self.x = initial_value  # Estimated RPM
        self.P = 1.0           # Error covariance
    
    def update(self, measurement):
        # Prediction update
        self.P += self.Q
        
        # Kalman gain
        K = self.P / (self.P + self.R)
        
        # Measurement update
        self.x = self.x + K * (measurement - self.x)
        self.P = (1 - K) * self.P
        
        return self.x