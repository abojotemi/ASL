import { json } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

const FASTAPI_PREDICT_URL = `${process.env.FASTAPI_BASE_URL || "https://asl-backend-qes4.onrender.com"}/predict`;

export const POST: RequestHandler = async ({ request, fetch }) => {
  try {
    const body = await request.json();

    if (!body?.image || typeof body.image !== "string") {
      return json({ error: "Missing image payload" }, { status: 400 });
    }

    const upstream = await fetch(FASTAPI_PREDICT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: body.image }),
    });

    const upstreamText = await upstream.text();

    return new Response(upstreamText, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    console.error("Proxy inference error:", error);
    return json(
      {
        error:
          `Unable to connect to inference backend at ${process.env.FASTAPI_PREDICT_URL}. Please try again later.`,
      },
      { status: 502 },
    );
  }
};
