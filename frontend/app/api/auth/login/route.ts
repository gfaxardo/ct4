const AUTH_UPSTREAM =
  process.env.AUTH_API_URL ?? 'https://api-int.yego.pro/api/auth/login';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(AUTH_UPSTREAM, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: body.username ?? '',
        password: body.password ?? '',
      }),
    });

    const data = await res.json().catch(() => ({}));
    return new Response(JSON.stringify(data), {
      status: res.status,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (err) {
    console.error('Auth proxy error:', err);
    return new Response(
      JSON.stringify({ error: 'Error de conexión con el servidor de autenticación' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
