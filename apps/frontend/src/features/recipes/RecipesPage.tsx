import * as React from 'react';
import { recipesApi, type Recipe } from './api';
import { useBilling } from '../billing';
import { PaidGate } from '../../shared/ui/PaidGate';

/**
 * Plan F §T33 — paid-only recipes list/edit/delete. Free users see the
 * PaidGate upgrade prompt; the actual REST endpoint is also paid-gated by
 * the gateway's FeatureGateFilter as a defense-in-depth measure.
 */
export function RecipesPage() {
  const { data: billing } = useBilling();
  return (
    <section data-testid="recipes-page">
      <h2>Recipes</h2>
      <PaidGate tier={billing?.tier} feature="Recipes">
        <RecipesList />
      </PaidGate>
    </section>
  );
}

function RecipesList() {
  const [recipes, setRecipes] = React.useState<Recipe[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    try {
      setRecipes(await recipesApi.list());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const onDelete = async (id: string) => {
    await recipesApi.remove(id);
    await refresh();
  };

  if (error) return <div role="alert">{error}</div>;
  if (recipes === null) return <div>Loading recipes…</div>;
  if (recipes.length === 0) return <p>No recipes yet. Save a pipeline from the workbench.</p>;

  return (
    <ul data-testid="recipes-list">
      {recipes.map((r) => (
        <li key={r.id} data-testid="recipe-row">
          <strong>{r.name}</strong>
          <button onClick={() => onDelete(r.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}
