from locust import HttpUser, task, between


class ApiUser(HttpUser):
    # Temps d'attente entre les actions (simule un humain)
    wait_time = between(1, 3)

    def on_start(self):
        """S'exécute une fois au démarrage de chaque utilisateur virtuel"""
        response = self.client.post("/login", json={
            "user": "testuser",
            "pass": "testpass"
        })

        if response.status_code == 200:
            self.token = response.json().get("access_token")
            # Ajout du token pour toutes les requêtes suivantes
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            print(f"Échec du login : {response.status_code}")

    @task(3)  # Poids plus élevé : exécuté plus souvent
    def acceder_route_protegee(self):
        """Simule l'accès à une API sécurisée"""
        self.client.get("/protected", name="/protected")

    @task(1)
    def voir_healthcheck(self):
        """Simule un check de santé"""
        self.client.get("/health", name="/health")
