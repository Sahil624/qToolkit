import { URLExt } from '@jupyterlab/coreutils';

import { ServerConnection } from '@jupyterlab/services';

/**
 * Call the API extension
 *
 * @param endPoint API REST end point for the extension
 * @param init Initial values for the request
 * @returns The response body interpreted as JSON
 */
export async function makeApiRequest<T = any>(
  endPoint = '',
  body: Object = {},
  init: RequestInit = {}
): Promise<T> {
  // Make request to Jupyter API
  const settings = ServerConnection.makeSettings();
  const requestUrl = URLExt.join(
    settings.baseUrl,
    'q-toolkit', // API Namespace
    endPoint
  );

  init.body = JSON.stringify(body);
  init.method = init.method ?? 'POST';
  init.headers = init.headers ?? {};
  (init.headers as any)['Content-Type'] = 'application/json';
  (init.headers as any)['Accept'] = 'application/json';

  let response: Response;
  try {
    response = await ServerConnection.makeRequest(requestUrl, init, settings);
  } catch (error) {
    throw new ServerConnection.NetworkError(error as any);
  }

  // let data: any = await response.text();

  // if (data.length > 0) {
  //   try {
  //     data = JSON.parse(data);
  //   } catch (error) {
  //     console.log('Not a JSON response body.', response);
  //   }
  // }

  if (!response.ok) {
    throw new ServerConnection.ResponseError(response, await response.text());
  }

  return response.json() as Promise<T>;
}
