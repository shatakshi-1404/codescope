import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../lib/endpoints";
import { fieldErrorsOf, messageOf } from "../../lib/errors";
import type { Project } from "../../lib/types";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import { Modal } from "../ui/Modal";
import { TextAreaField } from "../ui/TextAreaField";
import { useToast } from "../ui/Toast";

export function ProjectFormModal({ project, onClose }: { project?: Project; onClose: () => void }) {
  const editing = !!project;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();

  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: () => {
      const body = { name: name.trim(), description: description.trim() || null };
      return project ? api.updateProject(project.id, body) : api.createProject(body);
    },
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", saved.id] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(editing ? "Project updated." : `Project “${saved.name}” created.`);
      onClose();
      if (!editing) navigate(`/projects/${saved.id}`);
    },
    onError: (err) => {
      const server = fieldErrorsOf(err);
      if (Object.keys(server).length) setFieldErrors(server);
      else setError(messageOf(err));
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setFieldErrors({ name: "Give the project a name." });
      return;
    }
    setFieldErrors({});
    mutation.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={editing ? "Edit project" : "New project"}
      description={editing ? undefined : "A project groups repositories and the people who work on them."}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="project-form" loading={mutation.isPending}>
            {editing ? "Save changes" : "Create project"}
          </Button>
        </>
      }
    >
      <form id="project-form" onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && (
          <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </p>
        )}
        <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} error={fieldErrors.name} maxLength={120} placeholder="Payments platform" data-autofocus />
        <TextAreaField label="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} error={fieldErrors.description} maxLength={2000} placeholder="What does this project cover?" />
      </form>
    </Modal>
  );
}
