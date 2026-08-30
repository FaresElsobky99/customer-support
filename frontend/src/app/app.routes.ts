import { Routes } from '@angular/router';
import { Customers } from './components/customers/customers';
import { Dashboard } from './components/dashboard/dashboard';
import { Login } from './components/login/login';
import { Profile } from './components/profile/profile';
import { Tickets } from './components/tickets/tickets';
import { adminGuard } from './guards/admin.guard';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: Login },
  { path: 'dashboard', component: Dashboard, canActivate: [authGuard] },
  { path: 'profile', component: Profile, canActivate: [authGuard] },
  { path: 'tickets', component: Tickets, canActivate: [authGuard] },
  {
    path: 'customers',
    component: Customers,
    canActivate: [authGuard, adminGuard],
  },
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: '**', redirectTo: 'dashboard' },
];
