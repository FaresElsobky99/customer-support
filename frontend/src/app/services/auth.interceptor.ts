import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();
  const isApiRequest = request.url.startsWith(environment.apiUrl);
  const isLoginRequest = request.url.endsWith('/auth/login');

  const authenticatedRequest =
    token && isApiRequest && !isLoginRequest
      ? request.clone({
          setHeaders: { Authorization: `Bearer ${token}` },
        })
      : request;

  return next(authenticatedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !isLoginRequest) {
        authService.logout();
      }

      return throwError(() => error);
    }),
  );
};
