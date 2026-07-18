from django.utils import timezone

class StandardResponse:
    @staticmethod
    def list_response(results, count=None):
        return {
            "results": results,
            "count": count or len(results)
        }