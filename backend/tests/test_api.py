# backend/tests/test_api.py
"""
Testes TDD para a API REST
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Testes para endpoint de health check"""

    def test_health_check(self, client):
        """Deve retornar status healthy"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"


class TestLinksEndpoints:
    """Testes para endpoints de links"""

    def test_add_link_success(self, client, valid_youtube_url):
        """Deve adicionar link válido"""
        response = client.post("/api/links", json={"url": valid_youtube_url})
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.json()
        assert response.json()["url"] == valid_youtube_url

    def test_add_link_invalid_url(self, client, invalid_youtube_url):
        """Deve rejeitar URL inválida"""
        response = client.post("/api/links", json={"url": invalid_youtube_url})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_add_link_empty_url(self, client):
        """Deve rejeitar URL vazia"""
        response = client.post("/api/links", json={"url": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_get_all_links(self, client, sample_urls):
        """Deve retornar todos os links"""
        # Adiciona links
        for url in sample_urls:
            client.post("/api/links", json={"url": url})

        response = client.get("/api/links")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == len(sample_urls)

    def test_get_single_link(self, client, valid_youtube_url):
        """Deve retornar link específico"""
        # Adiciona link
        add_response = client.post("/api/links", json={"url": valid_youtube_url})
        link_id = add_response.json()["id"]

        response = client.get(f"/api/links/{link_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["url"] == valid_youtube_url

    def test_get_nonexistent_link(self, client):
        """Deve retornar 404 para link inexistente"""
        response = client.get("/api/links/nonexistent-id")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_link(self, client, valid_youtube_url):
        """Deve atualizar link existente"""
        # Adiciona link
        add_response = client.post("/api/links", json={"url": valid_youtube_url})
        link_id = add_response.json()["id"]

        new_url = "https://www.youtube.com/watch?v=9bZkp7q19f0"
        response = client.put(f"/api/links/{link_id}", json={"url": new_url})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["url"] == new_url

    def test_delete_link(self, client, valid_youtube_url):
        """Deve deletar link"""
        # Adiciona link
        add_response = client.post("/api/links", json={"url": valid_youtube_url})
        link_id = add_response.json()["id"]

        response = client.delete(f"/api/links/{link_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifica se foi deletado
        get_response = client.get(f"/api/links/{link_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_clear_all_links(self, client, sample_urls):
        """Deve limpar todos os links"""
        # Adiciona links
        for url in sample_urls:
            client.post("/api/links", json={"url": url})

        response = client.delete("/api/links")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifica se foi limpo
        get_response = client.get("/api/links")
        assert len(get_response.json()) == 0


class TestConversionEndpoints:
    """Testes para endpoints de conversão"""

    def test_start_conversion(self, client, valid_youtube_url):
        """Deve iniciar conversão"""
        # Adiciona link
        client.post("/api/links", json={"url": valid_youtube_url})

        response = client.post("/api/convert/start")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "converting"

    def test_start_conversion_no_links(self, client):
        """Deve falhar ao iniciar sem links"""
        response = client.post("/api/convert/start")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_stop_conversion(self, client, valid_youtube_url):
        """Deve parar conversão"""
        # Adiciona e inicia
        client.post("/api/links", json={"url": valid_youtube_url})
        client.post("/api/convert/start")

        response = client.post("/api/convert/stop")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "stopped"

    def test_get_conversion_status(self, client, valid_youtube_url):
        """Deve retornar status da conversão"""
        client.post("/api/links", json={"url": valid_youtube_url})

        response = client.get("/api/convert/status")
        assert response.status_code == status.HTTP_200_OK
        assert "is_converting" in response.json()


class TestDownloadEndpoints:
    """Testes para endpoints de download"""

    def test_download_completed_file(
        self, client, converter_service, valid_youtube_url
    ):
        """Deve fazer download de arquivo convertido"""
        import os

        # Cria arquivo de teste
        test_file = os.path.join(converter_service.downloads_dir, "test.mp3")
        with open(test_file, "wb") as f:
            f.write(b"fake mp3 content")

        # Adiciona task com arquivo
        task_id = converter_service.add_task(valid_youtube_url)
        converter_service.tasks[task_id].filename = "test.mp3"
        converter_service.tasks[task_id].status = "completed"

        response = client.get(f"/api/download/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "audio/mpeg"

    def test_download_nonexistent_file(self, client):
        """Deve retornar 404 para arquivo inexistente"""
        response = client.get("/api/download/nonexistent-id")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_pending_file(self, client, valid_youtube_url):
        """Deve retornar erro para arquivo não convertido"""
        # Adiciona link mas não converte
        add_response = client.post("/api/links", json={"url": valid_youtube_url})
        link_id = add_response.json()["id"]

        response = client.get(f"/api/download/{link_id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
