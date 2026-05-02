import grpc
import redis
import random
import logging
from concurrent import futures

import success_rate_pb2
import success_rate_pb2_grpc

# --- Config ---
REDIS_URL = "redis://172.27.93.89:6380/0"
GATEWAYS = ["flutterwave", "paystack", "monnify"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Redis connection ---
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_alpha_beta(merchant_id: str, gateway_id: str, payment_method: str):
    """
    Read successes and failures from Redis for a given
    merchant + gateway + payment method combination.
    Returns (alpha, beta) for Thompson Sampling.
    Alpha = successes + 1
    Beta  = failures  + 1
    """
    key = f"tx_window:{merchant_id}:{gateway_id}:{payment_method}"
    data = redis_client.hgetall(key)

    if not data:
        return 1.0, 1.0  # totally uncertain — no data yet

    successes = int(data.get("successes", 0))
    failures = int(data.get("failures", 0))

    alpha = successes + 1.0
    beta = failures + 1.0
    return alpha, beta


def thompson_sample(alpha: float, beta: float) -> float:
    """
    Draw one sample from Beta(alpha, beta).
    Higher alpha relative to beta = sample closer to 1.0 (good gateway).
    """
    return random.betavariate(alpha, beta)


def get_routing_mode(merchant_id: str, payment_method: str) -> str:
    key = f"routing_mode:{merchant_id}:{payment_method}"
    mode = redis_client.get(key)
    return mode if mode else "health_score"


class SuccessRateCalculatorServicer(
    success_rate_pb2_grpc.SuccessRateCalculatorServicer
):

    def FetchSuccessRate(self, request, context):
        """
        Called by Hyperswitch before every payment.
        Runs Thompson Sampling per gateway scoped to payment method.
        Returns ranked list of gateways.
        """
        merchant_id = request.id
        payment_method = request.params
        labels = list(request.labels)

        logger.info(
            f"FetchSuccessRate | merchant={merchant_id} "
            f"method={payment_method} gateways={labels}"
        )

        routing_mode = get_routing_mode(merchant_id, payment_method)
        is_mab = routing_mode == "mab"

        scores = []
        for gateway in labels:
            alpha, beta = get_alpha_beta(merchant_id, gateway, payment_method)
            sample = thompson_sample(alpha, beta)
            # Convert 0-1 sample to 0-100 score
            score = sample * 100.0
            scores.append((gateway, score))
            logger.info(
                f"  {gateway}: alpha={alpha} beta={beta} score={score:.2f}"
            )

        # Sort highest score first
        scores.sort(key=lambda x: x[1], reverse=True)

        labels_with_score = [
            success_rate_pb2.LabelWithScore(label=gw, score=sc)
            for gw, sc in scores
        ]

        routing_approach = (
            success_rate_pb2.RoutingApproach.EXPLOITATION
            if is_mab
            else success_rate_pb2.RoutingApproach.EXPLORATION
        )

        return success_rate_pb2.CalSuccessRateResponse(
            labels_with_score=labels_with_score,
            routing_approach=routing_approach,
        )

    def UpdateSuccessRateWindow(self, request, context):
        """
        Called by Hyperswitch after every payment outcome.
        Updates Redis tx_window for the gateway that was used.
        """
        merchant_id = request.id
        payment_method = request.params

        for label_status in request.labels_with_status:
            gateway = label_status.label
            success = label_status.status

            key = f"tx_window:{merchant_id}:{gateway}:{payment_method}"

            if success:
                redis_client.hincrby(key, "successes", 1)
                logger.info(f"UpdateWindow | {gateway} SUCCESS recorded")
            else:
                redis_client.hincrby(key, "failures", 1)
                logger.info(f"UpdateWindow | {gateway} FAILURE recorded")

        return success_rate_pb2.UpdateSuccessRateWindowResponse(
            status=success_rate_pb2.UpdateSuccessRateWindowResponse.WINDOW_UPDATION_SUCCEEDED
        )

    def InvalidateWindows(self, request, context):
        """
        Resets all tx_window data for a merchant.
        Useful when a gateway recovers from an outage.
        """
        merchant_id = request.id

        for gateway in GATEWAYS:
            for method in ["card", "bank_transfer", "bank_redirect"]:
                key = f"tx_window:{merchant_id}:{gateway}:{method}"
                redis_client.delete(key)
                logger.info(f"InvalidateWindows | deleted {key}")

        return success_rate_pb2.InvalidateWindowsResponse(
            status=success_rate_pb2.InvalidateWindowsResponse.WINDOW_INVALIDATION_SUCCEEDED
        )

    def FetchEntityAndGlobalSuccessRate(self, request, context):
        """
        Global cross-merchant tracking — not used in v1.
        Returns empty scores.
        """
        return success_rate_pb2.CalGlobalSuccessRateResponse(
            entity_scores_with_labels=[],
            global_scores_with_labels=[],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    success_rate_pb2_grpc.add_SuccessRateCalculatorServicer_to_server(
        SuccessRateCalculatorServicer(), server
    )
    server.add_insecure_port("[::]:8000")
    logger.info("RoutIQ MAB gRPC server starting on port 8000...")
    server.start()
    logger.info("Server ready. Waiting for requests...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()